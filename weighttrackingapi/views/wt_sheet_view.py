from django.http import HttpResponseServerError
from django.db import connection
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.decorators import action
from datetime import datetime
from weighttrackingapi.models import WeightSheet, Employee, Resident, Weight


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict used by SQL"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


class WeightSheetView(ViewSet):
    """Weight Tracking weight_sheet view"""

    def list(self, request):
        """Handle GET requests to get all weight_sheets

        Returns:
            Response -- JSON serialized list of weight_sheets
        """
        wt_sheets = WeightSheet.objects.all()
        # filtering weight_sheet by resident id and by date
        if "resident" in request.query_params and "date" in request.query_params:
            wt_sheets = wt_sheets.filter(
                resident=request.query_params['resident'], date=request.query_params['date'])
        # filtering weight_sheet by date
        if "date" in request.query_params:
            wt_sheets = wt_sheets.filter(date=request.query_params['date'])
        # filtering weight_sheet by resident id
        if "resident" in request.query_params:
            wt_sheets = wt_sheets.filter(
                resident=request.query_params['resident'])

        serializer = WeightSheetSerializer(wt_sheets, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk):
        """Handle GET requests for single weight sheet

        Returns:
            Response -- JSON serialized weight sheet
        """
        try:
            wt_sheet = WeightSheet.objects.get(pk=pk)
        except WeightSheet.DoesNotExist:
            return Response({'message': 'You sent an invalid weight_sheet ID'}, status=status.HTTP_404_NOT_FOUND)
        serializer = WeightSheetSerializer(wt_sheet)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        """Handle POST operations

        Returns
            Response -- JSON serialized weight sheet instance
        """
        employee = Employee.objects.get(user=request.auth.user)

        #Do not create a weightsheet if one already exists
        try:
            resident = Resident.objects.get(pk=request.data["resident"])
            WeightSheet.objects.get(date=request.data["date"], resident=resident)
            return Response({"msg": "Already exists"}, status=status.HTTP_400_BAD_REQUEST)
        except WeightSheet.DoesNotExist:
            wt_sheet = WeightSheet.objects.create(
            employee=employee,
            resident=resident,
            date=request.data["date"],
            reweighed=request.data["reweighed"],
            refused=request.data["refused"],
            not_in_room=request.data["not_in_room"],
            daily_wts=request.data["daily_wts"],
            show_alert=request.data["show_alert"],
            scale_type=request.data["scale_type"],
            final=request.data["final"]
        )
            wt_sheet.save()
            new_weight = Weight.objects.create(
                date=request.data["date"],
                resident=resident,
                weight=request.data["weight"]
            )
            new_weight.save()
            serializer = WeightSheetSerializer(wt_sheet)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        """Handle PUT operations for weight sheet

        Returns
            Response -- Empty body with 204 status code
        """
        employee = Employee.objects.get(user=request.auth.user)  
        wt_sheet = WeightSheet.objects.get(pk=pk)
        resident = Resident.objects.get(pk=request.data["resident"])
        wt_sheet.employee = employee
        wt_sheet.resident = resident
        wt_sheet.reweighed = request.data["reweighed"]
        wt_sheet.refused = request.data["refused"]
        wt_sheet.not_in_room = request.data["not_in_room"]
        wt_sheet.daily_wts = request.data["daily_wts"]
        wt_sheet.show_alert = request.data["show_alert"]
        wt_sheet.scale_type = request.data["scale_type"]
        wt_sheet.final = request.data["final"]
        wt_sheet.save()
        return Response({"msg": "Record updated"}, status=status.HTTP_204_NO_CONTENT)

    
    @action(detail=False, methods=['get', 'post', 'delete'])
    def detailedview_rd(self, request, pk=None):
        '''Shows all details for weightsheet'''
        # Joining the weight table (w) with the weightsheet table ws on resident_id and selecting columns from both tables
        # Store the result as a temporary table temp
        # Join this temp table with the resident table to get the first_name, last_name room_num etc from the resident table 
        with connection.cursor() as cursor:
            cursor.execute('''WITH temp AS (
    SELECT
        w.weight,
        w.id AS weight_id,
        ws.id AS weight_sheet_id,
        ws.final,
        ws.resident_id,
        ws.reweighed,
        ws.refused,
        ws.not_in_room,
        ws.daily_wts,
        ws.show_alert,
        ws.scale_type
    FROM
        weighttrackingapi_weight w
        JOIN weighttrackingapi_weightsheet ws ON ws.resident_id = w.resident_id
    WHERE
        w.date = %s
        AND ws.date = %s
)
SELECT
    r.first_name,
    r.last_name,
    r.room_num,
    temp.*
FROM
    temp
    JOIN weighttrackingapi_resident r ON temp.resident_id = r.id;
''', [request.query_params['date'], request.query_params['date']])
            #the results of the sql query are converted into an ordinary python dictionary using the Django-provided helper function (directly from the docs) DictFetchAll
            res = dictfetchall(cursor)
    
        return Response(res)
    

    
    @action(detail=False, methods=['post'])
    def create_all_weightsheets(self, request, pk=None):
        '''Creates ALL weightsheets for a given day Only if they don't already exist'''
        employee = Employee.objects.get(user=request.auth.user)
        residents = Resident.objects.all()
        i=0
        for resident in residents:
            existing_wt_sheet = WeightSheet.objects.filter(date=request.data["date"], resident=resident)
            if not  existing_wt_sheet.exists():
                wt_sheet = WeightSheet.objects.create(
                employee=employee,
                resident=resident,
                date=request.data["date"],
                reweighed=False,
                refused=False,
                not_in_room=False,
                daily_wts=False,
                show_alert=True,
                scale_type="",
                final=False)
                wt_sheet.save()
                new_weight = Weight.objects.create(
                date=request.data["date"],
                resident=resident,
                weight=0)
                new_weight.save()
                i+=1
                print("created")

        return Response({"msg": f"{i} Weightsheets created"}, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['delete'])
    def delete_all_by_date(self, request, pk=None):
        '''deletes weightsheets by date'''
        if "date" not in request.query_params:
            res = {"message": "A date must be provided"}
            return Response(res, status=status.HTTP_403_FORBIDDEN)
        date = request.query_params["date"]
        wt_sheets = WeightSheet.objects.filter(
            date=date)
        wt_sheets.delete()
        wts = Weight.objects.filter(date=date)
        wts.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['put'])
    def unsave_weightsheets(self, request, pk=None):
        '''Changes the final field to false for all weightsheets making them editable again'''
        if "date" not in request.data:
            res = {"message": "A date must be provided"}
            return Response(res, status=status.HTTP_403_FORBIDDEN)
        date = request.data["date"]
        wt_sheets = WeightSheet.objects.filter(
            date=date)
        for wt_sheet in wt_sheets:
            wt_sheet.final=0
            wt_sheet.save()
        return Response({"msg": "Records updated"}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['put'])
    def save_weightsheets(self, request, pk=None):
        '''Changes the final field to true for all weightsheets making them uneditable'''
        if "date" not in request.data:
            res = {"message": "A date must be provided"}
            return Response(res, status=status.HTTP_403_FORBIDDEN)
        date = request.data["date"]
        wt_sheets = WeightSheet.objects.filter(
            date=date)
        for wt_sheet in wt_sheets:
            wt_sheet.final = 1
            wt_sheet.save()
        return Response({"msg": "Records updated"}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def dates(self, request, pk=None):
        '''Gets all dates for which weightsheets have been done'''
        wt_sheets = WeightSheet.objects.all()
        serializer = WeightSheetDateSerializer(wt_sheets, many=True)

        dates = list(set([x["date"] for x in serializer.data]))
        dates.sort(key=lambda date: datetime.strptime(
            date, "%Y-%m-%d"), reverse=True)
        return Response({"dates": dates}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def finalized_dates(self, request, pk=None):
        '''Gets all dates for which weightsheets have been done'''
        wt_sheets = WeightSheet.objects.filter(final=1)
        serializer = WeightSheetDateSerializer(wt_sheets, many=True)

        dates = list(set([x["date"] for x in serializer.data]))
        dates.sort(key=lambda date: datetime.strptime(
            date, "%Y-%m-%d"), reverse=True)
        return Response({"dates": dates}, status=status.HTTP_200_OK)


    

class WeightSheetSerializer(serializers.ModelSerializer):
    """JSON serializer for weight_sheets"""
    class Meta:
        model = WeightSheet
        fields = ('id', 'employee', 'date', 'resident', 'final',
                  'reweighed', 'refused', 'not_in_room', 'daily_wts', 'show_alert', 'scale_type')
class WeightSerializer(serializers.ModelSerializer):
    """JSON serializer for weights"""
    class Meta:
        model = Weight
        fields = ('id', 'resident', 'date', 'weight')
        depth = 1


class WeightSheetDateSerializer(serializers.ModelSerializer):
    """JSON serializer for weight_sheets"""
    class Meta:
        model = WeightSheet
        fields = ('id','date','final')
