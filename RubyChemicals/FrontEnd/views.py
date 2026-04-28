from rest_framework import viewsets, status
from rest_framework.response import Response

from django.utils.dateparse import parse_date
from django.http import HttpResponse

from utils.decorators import handle_exceptions  # your custom decorators
from django.shortcuts import render, redirect
from functools import wraps
from django.contrib.auth import authenticate, login, logout
from Operations.models import *

def check_authentication(required_role=None):
    '''Checks if user is logged in or not.
    If required_role is passed (as str or list), will check for that as well.'''
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            user = request.user
            session_info = {}

            if hasattr(request, 'session'):
                session_info = {
                    'session_key': request.session.session_key,
                    'session_expiry': request.session.get_expiry_date(),
                    'session_data_keys': list(request.session.keys()),
                }

            if not user.is_authenticated:
                # logger.warning(f"Unauthenticated access attempt: {request.path}")
                return redirect('login-list')

            if required_role:
                # Convert to list if it's a string
                allowed_roles = required_role if isinstance(required_role, (list, tuple, set)) else [required_role]
                
                if getattr(user, "role", None) not in allowed_roles:
                    # logger.warning(
                    #     f"Unauthorized access: User {user.id} role {user.role} "
                    #     f"required {allowed_roles}"
                    # )
                    return Response(
                        {
                            "success": False,
                            "user_not_logged_in": False,
                            "user_unauthorized": True,
                            "data": None,
                            "error": f"User role must be one of {allowed_roles}"
                        }, status=status.HTTP_403_FORBIDDEN
                    )

            return view_func(self, request, *args, **kwargs)

        return _wrapped_view
    return decorator


class LoginViewSet(viewsets.ViewSet):

    @handle_exceptions
    def list(self, request):
        return render(request, 'login.html')


class AdminDashboardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'admin_dashboard.html')


class AccountsDashboardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'accounts_dashboard.html')


class ProductionDashboardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'production_dashboard.html')


class StockGroupViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'stock_groups.html')

class StockItemViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'stock_item.html')
        return render(request, 'stock_items.html')
    
class StockInwardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'stock_inward.html')        

class ProductionViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'production.html')

class DispatchViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'dispatch.html')
    
class ClientManagementViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'client_management.html')

class PettyCashViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'petty_cash.html')
    

class VendorManagementViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        return render(request, 'vendor_management.html')




class ExtraAddStockDetails(viewsets.ViewSet):

    
    @handle_exceptions
    @check_authentication()
    def list(self, request):
        
        stock_groups = ['AIWON CONSTRUCTION CHEMICALS',
        'CONTRACT MANUFACTURING',
        'KRIFIX',
        'PACKING MATERIALS',
        'RAW MATERIAL',
        'RUBY CHEMICALS',
        'SAMPLE',
        'SEMI FINISHED',
        'TECHNONICOL',
        'TRADING']

        stock_itmes = [
    {"stock_name": "AWON BOND - 40 KGS", "stock_group": "AIWON CONSTRUCTION CHEMICALS", "uom": "BAGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "NIRAFLEX - 30 KGS", "stock_group": "AIWON CONSTRUCTION CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "NIRAGROUT - 25 KGS", "stock_group": "AIWON CONSTRUCTION CHEMICALS", "uom": "BAGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "NIRAPRIME - 20 KGS", "stock_group": "AIWON CONSTRUCTION CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "NIRAPRIME - 5 KGS", "stock_group": "AIWON CONSTRUCTION CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "NIRASHIELD WB - 20 KGS.", "stock_group": "AIWON CONSTRUCTION CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "2K 150 1:2", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "2K 250 1:2", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "2K 90 1:2", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AC 30", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ANTIQUE MEMBRANE - KGS", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ARO ULTRA - 20 KGS", "stock_group": "CONTRACT MANUFACTURING", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "BL 1300", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "BL 900", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "BLU 1300", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "GROUT ADMIX", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "GROUT ADMIX - 300 ML", "stock_group": "CONTRACT MANUFACTURING", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "GROUT ADMIX - 400 ML", "stock_group": "CONTRACT MANUFACTURING", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "LAM 220", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "LAM 300", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "LATEX SH", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "NMI - BM", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "NMI - CFP", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "UC 350", "stock_group": "CONTRACT MANUFACTURING", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "KRIFIX 2K PRO", "stock_group": "KRIFIX", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "KRIFIX ACRYLIC", "stock_group": "KRIFIX", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "KRIFIX MEMBRANE", "stock_group": "KRIFIX", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "1 LTR BOTTLE", "stock_group": "PACKING MATERIALS", "uom": "NOS", "hsn": "392310", "gst": "18"},
{"stock_name": "10 LTR BUCKET", "stock_group": "PACKING MATERIALS", "uom": "NOS", "hsn": "392310", "gst": "18"},
{"stock_name": "1100 ML CONTAINER", "stock_group": "PACKING MATERIALS", "uom": "NOS", "hsn": "392310", "gst": "18"},
{"stock_name": "20 LITRES BUCKET", "stock_group": "PACKING MATERIALS", "uom": "NOS", "hsn": "39239090", "gst": "18"},
{"stock_name": "5 LTR BUCKET", "stock_group": "PACKING MATERIALS", "uom": "NOS", "hsn": "39233090", "gst": "18"},
{"stock_name": "50 LITRES CARBOY", "stock_group": "PACKING MATERIALS", "uom": "NOS", "hsn": "39233090", "gst": "18"},
{"stock_name": "500 ML BOTTLE", "stock_group": "PACKING MATERIALS", "uom": "NOS", "hsn": "392310", "gst": "18"},
{"stock_name": "500 ML CONTAINER", "stock_group": "PACKING MATERIALS", "uom": "NOS", "hsn": "392310", "gst": "18"},
{"stock_name": "2K POWDER BB MIX", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "2K POWDER BB MIX", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "2K POWDER TA MIX - 20 KGS", "stock_group": "RAW MATERIAL", "uom": "BAGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "2KA POWDER BB MIX", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "2KA POWDER TA MIX - 25 KGS", "stock_group": "RAW MATERIAL", "uom": "BAGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARCEE GROUT BB MIX", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "AARCEE GROUT MIX - 25 KGS.", "stock_group": "RAW MATERIAL", "uom": "BAGS", "hsn": "3214", "gst": "18"},
{"stock_name": "AARFIX BB MIX", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARFLEX BB MIX", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "AARPOXY WB - A - RESIN", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39073010", "gst": "18"},
{"stock_name": "AARPOXY WB - B - HARDENER", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "2921290", "gst": "18"},
{"stock_name": "AARSET BB MIX", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "AARTILE BB MIX", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "AH714 - HARDENER", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39089090", "gst": "18"},
{"stock_name": "B11 - RESIN", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39073010", "gst": "18"},
{"stock_name": "B47 - RESIN", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39073010", "gst": "18"},
{"stock_name": "BARIUM SULPHATE", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "28332700", "gst": "18"},
{"stock_name": "BL - NIKAFINA BLACK 683", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "32064990", "gst": "18"},
{"stock_name": "BP - Carbon Black Powder", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "28030010", "gst": "18"},
{"stock_name": "CALCITE", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "25309030", "gst": "5"},
{"stock_name": "CALCIUM STEARATE", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "29157090", "gst": "18"},
{"stock_name": "CF - CALCIUM FORMATE", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "29151290", "gst": "18"},
{"stock_name": "CF900", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "27101990", "gst": "18"},
{"stock_name": "CMC - CARBOXY METHYL CELLULOSE", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39123100", "gst": "18"},
{"stock_name": "CRYSTALOC BB MIX", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "DEG - DI ETHYLENE GLYCOL", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "29094100", "gst": "18"},
{"stock_name": "DF - H 207 - HARDNER", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39089090", "gst": "18"},
{"stock_name": "DF - H 485 - HARDENER", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "29212990", "gst": "18"},
{"stock_name": "DF - R 107 - RESIN", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39073010", "gst": "18"},
{"stock_name": "DF - R 385 - RESIN", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39073010", "gst": "18"},
{"stock_name": "DF H 205 - HARDNER", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39089090", "gst": "18"},
{"stock_name": "DF R 105 RESIN", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39089090", "gst": "18"},
{"stock_name": "DM", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "-", "gst": "-"},
{"stock_name": "DOLOMITE", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "25181000", "gst": "5"},
{"stock_name": "DROPOXY 7250 - RESIN", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39073010", "gst": "18"},
{"stock_name": "DROQUAMINE 730", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39119090", "gst": "18"},
{"stock_name": "EDTA", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "29212100", "gst": "18"},
{"stock_name": "EMULSIFIER 9.5", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "34021300", "gst": "18"},
{"stock_name": "GLASS FIBER - 3MM", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "7019", "gst": "18"},
{"stock_name": "GLASS FIBER POWDER", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "70010010", "gst": "5"},
{"stock_name": "HYDRATED LIME", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "25222000", "gst": "5"},
{"stock_name": "IM15", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "29420090", "gst": "18"},
{"stock_name": "J400U", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "MHEC", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39123919", "gst": "18"},
{"stock_name": "NIKAFINE BLUE 615", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "32041751", "gst": "18"},
{"stock_name": "NIKAFINE RED OXIDE 500", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "32064910", "gst": "18"},
{"stock_name": "NORNOL C12", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "29159090", "gst": "18"},
{"stock_name": "OXYLENE", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "29024100", "gst": "18"},
{"stock_name": "PCE (P)", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "38244010", "gst": "18"},
{"stock_name": "POLYAMIDE RESIN", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39081090", "gst": "18"},
{"stock_name": "PROCET DCT", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "29420090", "gst": "18"},
{"stock_name": "RC400", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39069090", "gst": "18"},
{"stock_name": "RC50", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39069090", "gst": "18"},
{"stock_name": "RC76", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39069090", "gst": "18"},
{"stock_name": "RCPUD", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39095000", "gst": "18"},
{"stock_name": "RDP", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39052900", "gst": "18"},
{"stock_name": "SHMP - SODIUM HEXA META PHOSPHATE", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "28352940", "gst": "18"},
{"stock_name": "SNF POWDER", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "29041030", "gst": "18"},
{"stock_name": "SODA ASH LIGHT", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "28362020", "gst": "18"},
{"stock_name": "SODIUM LIGNO SULPHATE", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "38040090", "gst": "18"},
{"stock_name": "SODIUM META SILICATE", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "28391900", "gst": "18"},
{"stock_name": "TALCUM", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "25262000", "gst": "5"},
{"stock_name": "TARTRIC ACID", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "29181200", "gst": "18"},
{"stock_name": "TEA - TRI ETHANOL AMINE", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "29221500", "gst": "18"},
{"stock_name": "TITANIUM DIOXIDE - TIO2", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "28230010", "gst": "18"},
{"stock_name": "V7650", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39069090", "gst": "18"},
{"stock_name": "V7660", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39069090", "gst": "18"},
{"stock_name": "V830", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39069090", "gst": "18"},
{"stock_name": "V960", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "39069090", "gst": "18"},
{"stock_name": "ZINC STEARATE", "stock_group": "RAW MATERIAL", "uom": "KGS", "hsn": "29157090", "gst": "18"},
{"stock_name": "2K PLUS - 30 KGS", "stock_group": "RUBY CHEMICALS", "uom": "PACK", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARCEE 2K - 35 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARCEE GROUT - 25 KGS", "stock_group": "RUBY CHEMICALS", "uom": "BAGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARCOAT - 20 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARCOAT - 5 KGS.", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARCRETE - 20 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARCRETE - 5 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARCRETE - 50 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARFIX GREY - 25 KGS", "stock_group": "RUBY CHEMICALS", "uom": "BAGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "AARFLEX GREY - 25 KGS", "stock_group": "RUBY CHEMICALS", "uom": "BAGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "AARJECT PU 2K - 5.5 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "39073090", "gst": "18"},
{"stock_name": "AARPOXY", "stock_group": "RUBY CHEMICALS", "uom": "PACK", "hsn": "39073010", "gst": "18"},
{"stock_name": "AARPOXY  WB", "stock_group": "RUBY CHEMICALS", "uom": "PACK", "hsn": "39073010", "gst": "18"},
{"stock_name": "AARSET - 25 KGS", "stock_group": "RUBY CHEMICALS", "uom": "BAGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "AARTILE - 40 KGS", "stock_group": "RUBY CHEMICALS", "uom": "BAGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "AQUALOC", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AQUALOC - 20 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AQUALOC - 5 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "BITULOC", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "BITULOC - 20 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "BITULOC - 5 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "BITULOC ULTRA", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "BITULOC ULTRA - 20 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "BITULOC ULTRA - 5 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "CRYSTALOC - 25 KGS", "stock_group": "RUBY CHEMICALS", "uom": "BAGS", "hsn": "38244010", "gst": "18"},
{"stock_name": "EXAFLEX - 30 KGS", "stock_group": "RUBY CHEMICALS", "uom": "PACK", "hsn": "38244090", "gst": "18"},
{"stock_name": "JOINTEX - 125 RM", "stock_group": "RUBY CHEMICALS", "uom": "ROLL", "hsn": "56031200", "gst": "5"},
{"stock_name": "JOINTEX - 200 RM", "stock_group": "RUBY CHEMICALS", "uom": "ROLL", "hsn": "56031200", "gst": "5"},
{"stock_name": "AARCEE MICON - 25 KGS", "stock_group": "RUBY CHEMICALS", "uom": "BAGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "PRIMA - 20 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "PRIMA - 5 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "PU FLEX - 4 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "32149090", "gst": "18"},
{"stock_name": "RAINPROOF", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "RAINPROOF - 20 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "RAINPROOF - 20 KGS - GREY", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "RAINPROOF - 20 KGS - TERRACOTTA", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "RAINPROOF - 5 KGS - GREY", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "RAINPROOF - 5 KGS - TERRACOTTA", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "RAINPROOF - 5 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "RAINPROOF - GREY", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "SBR LATEX - 20 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "SBR LATEX - 5 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRACOAT - 20 KGS - TERACOTTA", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRACOAT - 5 KGS - TERACOTTA", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRACOAT", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRACOAT - 20 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRACOAT - 20 KGS - GREY", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRACOAT - 5 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRACOAT - 5 KGS - GREY", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRACOAT - GREY", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRACOAT - GREY", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRACOAT - TERACOTTA", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "PRIMA", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARCRETE", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARCOAT", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "RAINPROOF - TERACOTTA", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "BITUSEAL", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "BITUSEAL - 5 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "BITUSEAL - 20 KGS", "stock_group": "RUBY CHEMICALS", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARPLAST - 25 KGS", "stock_group": "RUBY CHEMICALS", "uom": "BAGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "AARFIX WHITE - 25 KGS", "stock_group": "RUBY CHEMICALS", "uom": "BAGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "AARFLEX WHITE - 25 KGS", "stock_group": "RUBY CHEMICALS", "uom": "BAGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "SBR LATEX", "stock_group": "RUBY CHEMICALS", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "SAMPLE", "stock_group": "SAMPLE", "uom": "NOS", "hsn": "-", "gst": "-"},
{"stock_name": "SUSPENSE", "stock_group": "SAMPLE", "uom": "NOS", "hsn": "-", "gst": "-"},
{"stock_name": "2K 150 - L", "stock_group": "SEMI FINISHED", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "2K 250 - L", "stock_group": "SEMI FINISHED", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "2K 90 - L", "stock_group": "SEMI FINISHED", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "2K PLUS - L - 10 KGS", "stock_group": "SEMI FINISHED", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "2K POWDER - 20 KGS", "stock_group": "SEMI FINISHED", "uom": "BAGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "2KA POWDER - 25 KGS", "stock_group": "SEMI FINISHED", "uom": "BAGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARCEE 2K - L - 10 KGS", "stock_group": "SEMI FINISHED", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "AARFIX TA MIX - 25 KGS.", "stock_group": "SEMI FINISHED", "uom": "BAGS", "hsn": "3214", "gst": "18"},
{"stock_name": "AARFLEX TA MIX - 25 KGS.", "stock_group": "SEMI FINISHED", "uom": "BAGS", "hsn": "3214", "gst": "18"},
{"stock_name": "AARSET TA MIX - 25 KGS.", "stock_group": "SEMI FINISHED", "uom": "BAGS", "hsn": "3214", "gst": "18"},
{"stock_name": "AARTILE TA MIX - 40 KGS", "stock_group": "SEMI FINISHED", "uom": "BAGS", "hsn": "3214", "gst": "18"},
{"stock_name": "CRYSTALOC MIX - 25 KGS.", "stock_group": "SEMI FINISHED", "uom": "BAGS", "hsn": "38245090", "gst": "18"},
{"stock_name": "EXAFLEX - L - 10 KGS", "stock_group": "SEMI FINISHED", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "NIRAFLEX - L - 10 KGS", "stock_group": "SEMI FINISHED", "uom": "NOS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRACEM 2C - L", "stock_group": "SEMI FINISHED", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRACEM 2C FLEX - L", "stock_group": "SEMI FINISHED", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "CA 110", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "38244010", "gst": "18"},
{"stock_name": "GEOGELL GRID", "stock_group": "TECHNONICOL", "uom": "SQ MTR", "hsn": "39269099", "gst": "18"},
{"stock_name": "TECHNONICOL LATEX SBR", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "TECHNONICOL PRIMER 021", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "39073010", "gst": "18"},
{"stock_name": "TECHNONICOL TECHNOCRETE", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "TECHNONICOL ULTRASHIELD", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "TECHNONICOL ULTRATHANE", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "39091010", "gst": "18"},
{"stock_name": "TECHNONICOL ULTRATHANE PUD", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "TECHOMIX WL", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "38244010", "gst": "18"},
{"stock_name": "TN GEO TEXTILE 120 GSM", "stock_group": "TECHNONICOL", "uom": "SQ MTR", "hsn": "56039400", "gst": "12"},
{"stock_name": "TN POLYSULPHIDE SEALANT GG", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "32149090", "gst": "18"},
{"stock_name": "TN POLYSULPHIDE SEALANT PG", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "32149090", "gst": "18"},
{"stock_name": "TN ULTRASHIELD PRIMER", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "TN XPS CARBON PROOF 300", "stock_group": "TECHNONICOL", "uom": "SQ MTR", "hsn": "39211100", "gst": "18"},
{"stock_name": "ULTRACEM 2C", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRACEM 2C FLEX", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "38244090", "gst": "18"},
{"stock_name": "ULTRATHANE SUPER", "stock_group": "TECHNONICOL", "uom": "KGS", "hsn": "32141000", "gst": "18"},
{"stock_name": "AROSHIELD MAGNATACK 1.5 MM", "stock_group": "TRADING", "uom": "ROLL", "hsn": "68071090", "gst": "18"},
{"stock_name": "BITUMEN PRIMER", "stock_group": "TRADING", "uom": "NOS", "hsn": "27150090", "gst": "18"},
{"stock_name": "BITUMEN ROLLS", "stock_group": "TRADING", "uom": "ROLL", "hsn": "68071090", "gst": "18"},
{"stock_name": "FGM 45 - 50 SQM", "stock_group": "TRADING", "uom": "ROLL", "hsn": "70191100", "gst": "18"},
{"stock_name": "FLY ASH BLOCKS", "stock_group": "TRADING", "uom": "CBM", "hsn": "68159990", "gst": "12"},
{"stock_name": "GT 120", "stock_group": "TRADING", "uom": "SQ FT", "hsn": "5603", "gst": "12"},
{"stock_name": "PLUG POWDER", "stock_group": "TRADING", "uom": "KGS", "hsn": "32149010", "gst": "18"},
{"stock_name": "PU FOAM - 750 ML", "stock_group": "TRADING", "uom": "NOS", "hsn": "32141000", "gst": "18"},
{"stock_name": "PU SEALANT - 600 ML - GREY", "stock_group": "TRADING", "uom": "NOS", "hsn": "35069999", "gst": "18"},
{"stock_name": "PU SEALANT - 600 ML - WHITE", "stock_group": "TRADING", "uom": "NOS", "hsn": "35069999", "gst": "18"},
]


        created_stck_grp = {}

        for grp in stock_groups:
            new_stck, _ = StockGroup.objects.get_or_create(name=grp)            
            new_stck.save()
            created_stck_grp[grp] = new_stck
        
        itme_created = 1
        for itm in stock_itmes:
            try:
                print(itme_created)
                grp_obj = created_stck_grp[itm["stock_group"]]
                new_stock_item = StockItem.objects.create(
                    name=itm["stock_name"],
                    group=grp_obj,
                    unit=itm["uom"],
                    hsn_code=itm["hsn"],
                    gst=itm["gst"],
                )
                itme_created+=1
            except:
                print(f"error while adding this - {itm}")

        return HttpResponse("done")
