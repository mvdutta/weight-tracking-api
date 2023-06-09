from django.http import HttpResponseServerError
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.decorators import action
from weighttrackingapi.models import Message, Employee, EmployeeMessage


class MessageView(ViewSet):
    """Weight Tracking message view"""

    def list(self, request):
        """Handle GET requests to get all messages

        Returns:
            Response -- JSON serialized list of messages
        """
        message = Message.objects.all()

        # filtering message by date
        if "date_created" in request.query_params:
            message = message.filter(date_created=request.query_params['date_created'])

        serializer = MessageSerializer(message, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk):
        """Handle GET requests for single message

        Returns:
            Response -- JSON serialized message
        """
        try:
            message = Message.objects.get(pk=pk)
        except Message.DoesNotExist:
            return Response({'message': 'You sent an invalid message ID'}, status=status.HTTP_404_NOT_FOUND)
        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        """Handle POST operations

        Returns
            Response -- JSON serialized message instance
        """
        sender = Employee.objects.get(user=request.auth.user)
        recipients =request.data["recipients"]
        message = Message.objects.create(
            subject=request.data["subject"],
            message_body=request.data["message_body"],
            date_created=request.data["date_created"],
            read=request.data["read"],
            deleted=request.data["deleted"],
            sender = sender
        )
        message.save()
        serializer = MessageSerializer(message)
        new_message_id = serializer.data['id']
        for recipient in recipients:
            employee_message=EmployeeMessage.objects.create(
                message = Message.objects.get(pk=new_message_id),
                sender = sender,
                recipient = Employee.objects.get(pk=recipient)
            )
            employee_message.save()

        return Response({"msg": "Message sent"}, status=status.HTTP_201_CREATED)

    def update(self, request, pk):
        """Handle PUT operations for message

        Returns
            Response -- Empty body with 204 status code
        """
        message = Message.objects.get(pk=pk)
        message.read = request.data["read"]
        message.deleted = request.data["deleted"]
        message.save()

        return Response(None, status=status.HTTP_204_NO_CONTENT)
    
    def destroy(self, request, pk):
        """Handle DELETE requests for messages

        Returns:
            Response: None with 204 status code
        """
        message = Message.objects.get(pk=pk)
        message.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['put'])
    def togglereadstatus(self, request, pk):
        """Toggles message from unread to read and vice versa"""
        message = Message.objects.get(pk=pk)
        message.read = not message.read
        message.save()
        return Response(None, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['put'])
    def changeunreadtoread(self, request, pk):
        """changes message from unread to read"""
        message = Message.objects.get(pk=pk)
        if not message.read:
            message.read = True
            message.save()
        return Response(None, status=status.HTTP_204_NO_CONTENT)

class EmployeeSerializer(serializers.ModelSerializer):
    """JSON serializer for message sender"""
    class Meta:
        model = Employee
        fields = ('id', 'user')
        depth = 1

class MessageSerializer(serializers.ModelSerializer):
    """JSON serializer for messages"""
    sender = EmployeeSerializer(many=False)
    class Meta:
        model = Message
        fields = ('id', 'subject', 'message_body', 'date_created', 'read', 'deleted', 'sender')
        depth = 1

