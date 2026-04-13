from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import ClientProfile, ClientAddress
from .serializers import ClientProfileSerializer, ClientAddressSerializer, ClientProfileListSerializer
from utils.decorators import handle_exceptions, check_authentication
from django.db.models import Q


class ClientProfileViewSet(viewsets.ModelViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """List all clients"""
        clients = ClientProfile.objects.all().order_by('-created_at')
        serializer = ClientProfileListSerializer(clients, many=True)
        
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": serializer.data,
            "error": None
        }, status=200)

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        """Get single client with addresses"""
        try:
            client = ClientProfile.objects.get(id=pk)
            serializer = ClientProfileSerializer(client)
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": serializer.data,
                "error": None
            }, status=200)
        except ClientProfile.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Client not found"
            }, status=404)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """Create new client"""
        serializer = ClientProfileSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": serializer.data,
                "error": None
            }, status=201)
        
        return Response({
            "success": False,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": None,
            "error": serializer.errors
        }, status=400)

    @handle_exceptions
    @check_authentication()
    def update(self, request, pk=None):
        """Update client"""
        try:
            client = ClientProfile.objects.get(id=pk)
            serializer = ClientProfileSerializer(client, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                
                return Response({
                    "success": True,
                    "user_not_logged_in": False,
                    "user_unauthorized": False,
                    "data": serializer.data,
                    "error": None
                }, status=200)
            
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": serializer.errors
            }, status=400)
        except ClientProfile.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Client not found"
            }, status=404)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        """Delete client"""
        try:
            client = ClientProfile.objects.get(id=pk)
            client.delete()
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": None
            }, status=200)
        except ClientProfile.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Client not found"
            }, status=404)

    @handle_exceptions
    @check_authentication()
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search clients by company name"""
        query = request.query_params.get('q', '')
        
        if query:
            clients = ClientProfile.objects.filter(
                Q(company_name__icontains=query) | 
                Q(contact_person__icontains=query) |
                Q(email__icontains=query)
            ).order_by('company_name')
        else:
            clients = ClientProfile.objects.all().order_by('company_name')
        
        serializer = ClientProfileListSerializer(clients, many=True)
        
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": serializer.data,
            "error": None
        }, status=200)


class ClientAddressViewSet(viewsets.ModelViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """List addresses for a client"""
        client_id = request.query_params.get('client_id')
        
        if not client_id:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "client_id required"
            }, status=400)
        
        addresses = ClientAddress.objects.filter(client_id=client_id).order_by('-is_default')
        serializer = ClientAddressSerializer(addresses, many=True)
        
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": serializer.data,
            "error": None
        }, status=200)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """Create new address for client"""
        serializer = ClientAddressSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": serializer.data,
                "error": None
            }, status=201)
        
        return Response({
            "success": False,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": None,
            "error": serializer.errors
        }, status=400)

    @handle_exceptions
    @check_authentication()
    def update(self, request, pk=None):
        """Update address"""
        try:
            address = ClientAddress.objects.get(id=pk)
            serializer = ClientAddressSerializer(address, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                
                return Response({
                    "success": True,
                    "user_not_logged_in": False,
                    "user_unauthorized": False,
                    "data": serializer.data,
                    "error": None
                }, status=200)
            
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": serializer.errors
            }, status=400)
        except ClientAddress.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Address not found"
            }, status=404)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        """Delete address"""
        try:
            address = ClientAddress.objects.get(id=pk)
            address.delete()
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": None
            }, status=200)
        except ClientAddress.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Address not found"
            }, status=404)
