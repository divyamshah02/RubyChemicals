from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import VendorProfile, VendorAddress
from .serializers import *
from utils.decorators import handle_exceptions, check_authentication
from django.db.models import Q


class VendorProfileViewSet(viewsets.ModelViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """List all vendors"""
        vendors = VendorProfile.objects.all().order_by('-created_at')
        serializer = VendorProfileListSerializer(vendors, many=True)
        
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
        """Get single vendor with addresses"""
        try:
            vendor = VendorProfile.objects.get(id=pk)
            serializer = VendorProfileSerializer(vendor)
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": serializer.data,
                "error": None
            }, status=200)
        except VendorProfile.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Vendor not found"
            }, status=404)

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """Create new vendor"""
        serializer = VendorProfileSerializer(data=request.data)
        
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
        """Update vendor"""
        try:
            vendor = VendorProfile.objects.get(id=pk)
            serializer = VendorProfileSerializer(vendor, data=request.data, partial=True)
            
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
        except VendorProfile.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Vendor not found"
            }, status=404)

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        """Delete vendor"""
        try:
            vendor = VendorProfile.objects.get(id=pk)
            vendor.delete()
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": None
            }, status=200)
        except VendorProfile.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Vendor not found"
            }, status=404)

    @handle_exceptions
    @check_authentication()
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search vendors by company name"""
        query = request.query_params.get('q', '')
        
        if query:
            vendors = VendorProfile.objects.filter(
                Q(company_name__icontains=query) | 
                Q(contact_person__icontains=query) |
                Q(email__icontains=query)
            ).order_by('company_name')
        else:
            vendors = VendorProfile.objects.all().order_by('company_name')
        
        serializer = VendorProfileListSerializer(vendors, many=True)
        
        return Response({
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": serializer.data,
            "error": None
        }, status=200)


class VendorAddressViewSet(viewsets.ModelViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """List addresses for a vendor"""
        vendor_id = request.query_params.get('vendor_id')
        
        if not vendor_id:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "vendor_id required"
            }, status=400)
        
        addresses = VendorAddress.objects.filter(vendor_id=vendor_id).order_by('-is_default')
        serializer = VendorAddressSerializer(addresses, many=True)
        
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
        """List addresses for a vendor"""
        vendor_id = pk
        
        if not vendor_id:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "vendor_id required"
            }, status=400)
        
        addresses = VendorAddress.objects.get(id=vendor_id)
        serializer = VendorAddressSerializer(addresses)
        
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
        """Create new address for vendor"""
        serializer = VendorAddressSerializer(data=request.data)
        
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
            address = VendorAddress.objects.get(id=pk)
            serializer = VendorAddressSerializer(address, data=request.data, partial=True)
            
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
        except VendorAddress.DoesNotExist:
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
            address = VendorAddress.objects.get(id=pk)
            address.delete()
            
            return Response({
                "success": True,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": None
            }, status=200)
        except VendorAddress.DoesNotExist:
            return Response({
                "success": False,
                "user_not_logged_in": False,
                "user_unauthorized": False,
                "data": None,
                "error": "Address not found"
            }, status=404)
