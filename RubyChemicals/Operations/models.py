from django.db import models
from django.utils import timezone


# Create your models here.
class StockGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

class StockItem(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('pcs', 'Pieces'),

        ('BAGS', 'BAGS'),
        ('NOS', 'NOS'),
        ('GRAMS', 'GRAMS'),
        ('KGS', 'KGS'),
        ('PACK', 'PACK'),
        ('ROLL', 'ROLL'),
        ('SQ FT', 'SQ FT'),
        ('SQ MTR', 'SQ MTR'),
        ('CBM', 'CBM'),
    ]

    name = models.CharField(max_length=255)
    group = models.ForeignKey(
        StockGroup,
        on_delete=models.PROTECT,
        related_name='items'
    )
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES)
    hsn_code = models.CharField(max_length=10, null=True, blank=True)
    gst = models.CharField(max_length=4, null=True, blank=True)

    current_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('name', 'group')

    def __str__(self):
        return f"{self.name} ({self.group.name})"


class StockLog(models.Model):
    """
    Maintains historical stock snapshot for each date
    stock_data format: {
        "stock_item_id": {"name": "...", "qty": X.XX, "unit": "..."},
        ...
    }
    """
    date = models.DateField(unique=True, db_index=True)
    stock_data = models.JSONField(default=dict)  # {stock_id: {name, qty, unit}}
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Stock Log - {self.date}"


class VendorProfile(models.Model):
    company_name = models.CharField(max_length=200, unique=True)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    gst_no = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.company_name


class VendorAddress(models.Model):
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    address_type = models.CharField(
        max_length=20,
        choices=[('billing', 'Billing'), ('shipping', 'Shipping'), ('other', 'Other')],
        default='shipping'
    )
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')
    
    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.vendor.company_name} - {self.address_type}"


class VendorInward(models.Model):
    inward_code = models.CharField(max_length=20, unique=True, editable=False)
    inward_date = models.DateField()
    
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.PROTECT
    )
    
    # Accounting Details
    accounted = models.BooleanField(default=False, help_text="Mark as accounted in books")
    invoice_number = models.CharField(max_length=100, blank=True, null=True, help_text="Invoice number for accounting")
    invoice_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pdf = models.FileField(upload_to='inward_pdfs/', blank=True, null=True, help_text="Invoice/Inward PDF")
    image = models.ImageField(upload_to='inward_images/', blank=True, null=True, help_text="Inward receipt/proof image")
    
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.inward_code:
            # Generate auto inward code
            from django.db.models import F
            last_inward = VendorInward.objects.filter(
                created_at__year=timezone.now().year
            ).order_by('-id').first()
            
            year = timezone.now().year % 100
            month = timezone.now().month
            sequence = 1 if not last_inward else int(last_inward.inward_code.split('-')[-1]) + 1
            self.inward_code = f"INWD-{year}{month:02d}-{sequence:05d}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Inward - {self.inward_code}"


class StockInward(models.Model):
    inward_entry = models.ForeignKey(
        VendorInward,
        on_delete=models.CASCADE,
        related_name='items',
        null=True,
        blank=True
    )
    
    date = models.DateField()
    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.PROTECT,
        related_name='inwards'
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Inward - {self.stock_item.name}"

class StockAdjustment(models.Model):
    ADJUSTMENT_TYPE = [
        ('increase', 'Increase'),
        ('decrease', 'Decrease'),
    ]

    date = models.DateField()
    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.PROTECT,
        related_name='adjustments'
    )
    adjustment_type = models.CharField(max_length=10, choices=ADJUSTMENT_TYPE)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    reason = models.CharField(max_length=255)

    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Adjustment - {self.stock_item.name}"

class ProductionCard(models.Model):
    production_code = models.CharField(max_length=20, unique=True)
    production_date = models.DateField()
    product_name = models.CharField(max_length=255, blank=True)
    production_incharge = models.CharField(max_length=255, blank=True)
    
    total_output_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )
    
    total_loss = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )
    
    unit = models.CharField(max_length=10, default='kg', choices=[
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('pcs', 'Pieces'),
    ])
    
    accounted = models.BooleanField(default=False)
    
    remarks = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.production_code


class ProductionBatch(models.Model):
    batch_code = models.CharField(max_length=20, unique=True)
    production_card = models.ForeignKey(
        ProductionCard,
        on_delete=models.CASCADE,
        related_name='batches',
        null=True,
        blank=True
    )
    
    product = models.ForeignKey(
        StockItem,
        on_delete=models.PROTECT,
        related_name='production_batches'
    )
    
    output_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3
    )
    loss_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )
    
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.batch_code


class ProductionConsumption(models.Model):
    production_card = models.ForeignKey(
        ProductionCard,
        on_delete=models.CASCADE,
        related_name='consumptions',
        null=True,
        blank=True
    )
    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.PROTECT
    )
    quantity_used = models.DecimalField(
        max_digits=12,
        decimal_places=3
    )
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.stock_item.name}"


# Petty Cash Models
class PettyCashAccount(models.Model):
    CASH_TYPE_CHOICES = [
        ('office', 'Office'),
        ('factory', 'Factory'),
    ]
    
    cash_type = models.CharField(max_length=20, choices=CASH_TYPE_CHOICES, unique=True)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Petty Cash - {self.get_cash_type_display()}"

class ExpenseHead(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name

class PettyCash(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('advance', 'Advance'),
        ('part', 'Part'),
        ('final', 'Final'),
    ]
    
    PAID_VIA_CHOICES = [
        ('online', 'Online'),
        ('cash', 'Cash'),
    ]
    
    cash_account = models.ForeignKey(
        PettyCashAccount,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='transactions'
    )
    expense_head = models.ForeignKey(
        ExpenseHead,
        on_delete=models.PROTECT,
        related_name='expenses',
        null=True,
        blank=True
    )
    expense_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=[('credit', 'Credit'), ('debit', 'Debit')])
    notes = models.TextField(blank=True)
    
    # New Fields
    to = models.CharField(max_length=255, blank=True, null=True, help_text="Direct recipient name")
    paid_via = models.CharField(max_length=20, choices=PAID_VIA_CHOICES, blank=True, null=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, blank=True, null=True)
    particulars = models.TextField(blank=True, null=True, help_text="Details other than remarks")
    paid_by = models.CharField(max_length=255, blank=True, null=True, help_text="Person who made payment")
    
    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True, help_text="Soft delete flag - False means deleted")
    
    def __str__(self):
        return f"{self.cash_account.get_cash_type_display()} - {self.amount}"


class PettyCashLog(models.Model):
    """
    Maintains historical petty cash balance snapshot for each date per cash account
    Data format: {
        "cash_type": {"opening_balance": X.XX, "closing_balance": Y.YY, "total_debit": Z.ZZ, "total_credit": A.AA}
    }
    """
    date = models.DateField(db_index=True)
    cash_data = models.JSONField(default=dict)  # {cash_type: {opening_bal, closing_bal, total_debit, total_credit}}
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        unique_together = ('date',)

    def __str__(self):
        return f"Petty Cash Log - {self.date}"


class ClientProfile(models.Model):
    company_name = models.CharField(max_length=200, unique=True)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    gst_no = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.company_name


class ClientAddress(models.Model):
    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    address_type = models.CharField(
        max_length=20,
        choices=[('billing', 'Billing'), ('shipping', 'Shipping'), ('other', 'Other')],
        default='shipping'
    )
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')
    contact_name = models.CharField(max_length=255, null=True, blank=True)
    contact_number = models.CharField(max_length=255, null=True, blank=True)
    gst_no = models.CharField(max_length=255, null=True, blank=True)

    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.client.company_name} - {self.address_type}"

class Dispatch(models.Model):
    dispatch_code = models.CharField(max_length=20, unique=True)
    dispatch_date = models.DateField()
    
    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    shipping_address = models.ForeignKey(
        ClientAddress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Vehicle & Freight Details
    vehicle_type = models.CharField(max_length=100, blank=True, help_text="e.g., Truck, Van, Bike")
    vehicle_number = models.CharField(max_length=50, blank=True)
    freight_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Accounting Details
    accounted = models.BooleanField(default=False, help_text="Mark as accounted in books")
    invoice_number = models.CharField(max_length=100, blank=True, null=True, help_text="Invoice number for accounting")
    pdf = models.FileField(upload_to='dispatch_pdfs/', blank=True, null=True, help_text="Invoice/Dispatch PDF")
    
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.dispatch_code:
            # Generate auto dispatch code
            from django.db.models import F
            last_dispatch = Dispatch.objects.filter(
                created_at__year=timezone.now().year
            ).order_by('-id').first()
            
            sequence = 1 if not last_dispatch else int(last_dispatch.dispatch_code.split('-')[-1]) + 1
            self.dispatch_code = f"{sequence:03d}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Dispatch - {self.dispatch_code}"


class DispatchItem(models.Model):
    dispatch = models.ForeignKey(
        Dispatch,
        on_delete=models.CASCADE,
        related_name='items'
    )
    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.PROTECT
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=10, default='kg', choices=[
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('pcs', 'Pieces'),
    ])
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.stock_item.name} - {self.quantity} {self.unit}"


class Lead(models.Model):

    PARTY_TYPE_CHOICES = [
        ('dealer', 'Dealer'),
        ('distributor', 'Distributor'),
        ('waterproofing_applicator', 'Waterproofing Applicator'),
        ('tile_adhesive_applicator', 'Tile Adhesive Applicator'),
        ('oem', 'OEM'),
        ('architect', 'Architect'),
        ('interior_designer', 'Interior Designer'),
        ('pmc', 'PMC'),
        ('builder_project', 'Builder Project'),
        ('individual_project', 'Individual Project'),
        ('bungalow', 'Bungalow'),
        ('structural_consultant', 'Structural Consultant'),
        ('mepf_consultant', 'MEPF Consultant'),
        ('other', 'Other'),
    ]

    LEAD_STATUS_CHOICES = [
        ('new_lead', 'New Lead'),
        ('contacted', 'Contacted'),
        ('details_shared', 'Details Shared'),
        ('appointment_fixed', 'Appointment Fixed'),
        ('visit_done', 'Visit Done'),
        ('proposal_sent', 'Proposal Sent'),
        ('sample_to_be_done', 'Sample To Be Done'),
        ('sample_done', 'Sample Done'),
        ('negotiation_followup', 'Negotiation / Follow-up'),
        ('won', 'Won'),
        ('repeat_order', 'Repeat Order'),
        ('closed_lost', 'Closed – Lost'),
        ('closed_forwarded', 'Closed – Forwarded'),
        ('on_hold', 'On Hold'),
        ('future_potential', 'Future Potential'),
        ('other', 'Other'),
    ]

    lead_id = models.PositiveIntegerField(unique=True, editable=False)
    date_of_connect = models.DateField(null=True, blank=True)
    lead_source = models.CharField(max_length=255, blank=True)

    # ── NEW: sub-department linkage ──────────────────────────────────────────
    # nullable so existing rows without a sub-department stay valid.
    # All pre-existing leads should be migrated to sub_department_id=1 (OEM).
    sub_department = models.ForeignKey(
        'LeadSubDepartment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads',
        help_text="Leads sub-department (OEM / RC / Applications / …)"
    )

    party_type = models.CharField(max_length=50, choices=PARTY_TYPE_CHOICES)
    party_name = models.CharField(max_length=200)
    location = models.CharField(max_length=255, blank=True)

    contact_person = models.CharField(max_length=100, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    lead_status = models.CharField(
        max_length=50,
        choices=LEAD_STATUS_CHOICES,
        default='new_lead'
    )

    remarks = models.TextField(blank=True, help_text="Remarks / Briefing about the lead")

    # Next follow-up tracking
    next_followup = models.DateTimeField(null=True, blank=True)

    # Forwarded to (used when status = closed_forwarded)
    forwarded_to = models.CharField(max_length=255, blank=True)

    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads_created'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.lead_id:
            last = Lead.objects.order_by('-id').first()
            self.lead_id = 1 if not last else last.lead_id + 1

        # if self.sub_department is None:
        if self.party_type == 'oem':
            self.sub_department = LeadSubDepartment.objects.filter(code='OEM').first()
        else:
            self.sub_department = LeadSubDepartment.objects.filter(code='RC').first()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.lead_id} - {self.party_name}"


class LeadCallRecord(models.Model):
    """Tracks every call / connect made for a lead"""

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='call_records'
    )

    call_date = models.DateField()
    contact_number = models.CharField(max_length=20, blank=True)
    briefing = models.TextField(help_text="What was discussed in this call")

    lead_status = models.CharField(
        max_length=50,
        choices=Lead.LEAD_STATUS_CHOICES,
        blank=True,
        help_text="Lead status after this call"
    )

    next_followup = models.DateTimeField(
        null=True, blank=True,
        help_text="Next follow-up date & time after this call"
    )

    follow_up_done = models.BooleanField(
        default=False,
        help_text="Mark as True when the follow-up is completed"
    )

    forwarded_to = models.CharField(
        max_length=255, blank=True,
        help_text="Email/name of person forwarded to (when status = Closed-Forwarded)"
    )

    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-call_date', '-created_at']

    def __str__(self):
        return f"Call for {self.lead.lead_id} on {self.call_date}"


# ─────────────────────────────────────────────────────────────────────────────
# 1. LeadSubDepartment
# ─────────────────────────────────────────────────────────────────────────────

class LeadSubDepartment(models.Model):
    """
    Fully dynamic sub-departments under the Leads/Sales department.
    Seed data: OEM (id=1), RC, Applications — admins can add more at any time.
    """
    name        = models.CharField(max_length=100, unique=True)
    code        = models.CharField(max_length=20, unique=True,
                                   help_text="Short code, e.g. OEM / RC / APP")
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ───────────────────────────────────────────────────────��─────────────────────
# 2. SubDeptStockItem
# ─────────────────────────────────────────────────────────────────────────────

class SubDeptStockItem(models.Model):
    """
    Stock items specific to a LeadSubDepartment.
    Independent from the main Operations StockItem catalogue.
    """
    UOM_CHOICES = [
        ('NOS',    'NOS'),
        ('KGS',    'KGS'),
        ('BAGS',   'BAGS'),
        ('GRAMS',  'GRAMS'),
        ('PACK',   'PACK'),
        ('ROLL',   'ROLL'),
        ('SQ FT',  'SQ FT'),
        ('SQ MTR', 'SQ MTR'),
        ('CBM',    'CBM'),
        ('LTR',    'LTR'),
        ('ML',     'ML'),
        ('PCS',    'PCS'),
        ('MTR',    'MTR'),
    ]

    sub_department = models.ForeignKey(
        LeadSubDepartment,
        on_delete=models.CASCADE,
        related_name='stock_items'
    )
    product_name = models.CharField(max_length=255)
    hsn_code     = models.CharField(max_length=20, blank=True, null=True)
    rate         = models.DecimalField(max_digits=12, decimal_places=2,
                                       null=True, blank=True,
                                       help_text="Default rate; can be overridden in quotation")
    uom          = models.CharField(max_length=20, default='NOS',
                                    verbose_name="Unit of Measurement")
    warranty     = models.CharField(max_length=100, blank=True, null=True,
                                    help_text="Optional warranty info, e.g. '1 Year', '6 Months'")
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('sub_department', 'product_name')
        ordering = ['product_name']

    def __str__(self):
        return f"{self.product_name} ({self.sub_department.code})"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Quotation + QuotationItem
#    FK → Lead  (uses the existing Lead model, not DeptLead)
# ─────────────────────────────────────────────────────────────────────────────

class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft',    'Draft'),
        ('sent',     'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    quotation_no   = models.CharField(max_length=30, unique=True, editable=False)
    lead           = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='quotations'
    )
    quotation_date = models.DateField()
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes          = models.TextField(blank=True)

    # Address / billing info (free-text for flexibility)
    billing_address  = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)

    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='quotations_created'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active  = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.quotation_no:
            from django.utils import timezone as tz
            year   = tz.now().year % 100
            month  = tz.now().month
            last   = Quotation.objects.filter(
                created_at__year=tz.now().year
            ).order_by('-id').first()
            seq = 1 if not last else int(last.quotation_no.split('-')[-1]) + 1
            # Use lead's sub_department code if available, else fallback to 'QT'
            dept_code = 'QT'
            if self.lead_id:
                try:
                    dept_code = Lead.objects.get(pk=self.lead_id).sub_department.code
                except (Lead.DoesNotExist, AttributeError):
                    pass
            self.quotation_no = f"QT-{dept_code}-{year}{month:02d}-{seq:04d}"
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.quotation_no


class QuotationItem(models.Model):
    quotation   = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name='items'
    )
    # Now nullable — application-area items may not have a catalogue entry
    stock_item  = models.ForeignKey(
        SubDeptStockItem,
        on_delete=models.PROTECT,
        related_name='quotation_items',
        null=True, blank=True,
    )
    # Free-text name used when stock_item is NULL
    product_name = models.CharField(max_length=255, blank=True, help_text="Used when stock_item is not linked")
    hsn_code = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    # Rate is copied from SubDeptStockItem but fully editable per-line
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    uom = models.CharField(max_length=20, blank=True, help_text="Copied from item but can be overridden")
    scope = models.CharField(
                max_length=100,
                blank=True,
                default='',
                help_text="Scope of work, e.g. 'LABOUR + MATERIAL', 'LABOUR ONLY'")
    warranty = models.CharField(max_length=100, blank=True, help_text="Warranty info, e.g. '1 Year'")
    application_area = models.CharField(max_length=100, null=True, blank=True, help_text="Optional application area for this item")
    description = models.TextField(blank=True, help_text="Optional line-level description")
    is_active = models.BooleanField(default=True)

    def get_product_name(self):
        return self.stock_item.product_name if self.stock_item else self.product_name

    @property
    def total(self):
        return self.quantity * self.rate

    def __str__(self):
        return f"{self.get_product_name()} × {self.quantity}"

# ─────────────────────────────────────────────────────────────────────────────
# 4. SampleRequisite + SampleRequisiteItem
#    FK → Lead
# ─────────────────────────────────────────────────────────────────────────────

class SampleRequisite(models.Model):
    STATUS_CHOICES = [
        ('pending',        'Pending'),
        ('partial_sent',   'Partial Sent'),
        ('sent',           'Sent'),
    ]

    sr_no     = models.CharField(max_length=30, unique=True, editable=False)
    lead      = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='sample_requisites'
    )
    sr_date   = models.DateField()
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Delivery address / contact
    delivery_address = models.TextField(blank=True)
    contact_name     = models.CharField(max_length=100, blank=True)
    contact_number   = models.CharField(max_length=20, blank=True)

    notes      = models.TextField(blank=True)
    # Factory marks this once sample is dispatched
    sent_to_factory_at = models.DateTimeField(null=True, blank=True)
    factory_remarks    = models.TextField(blank=True)

    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sr_created'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active  = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.sr_no:
            from django.utils import timezone as tz
            year   = tz.now().year % 100
            month  = tz.now().month
            last   = SampleRequisite.objects.filter(
                created_at__year=tz.now().year
            ).order_by('-id').first()
            seq = 1 if not last else int(last.sr_no.split('-')[-1]) + 1
            dept_code = 'SR'
            if self.lead_id:
                try:
                    dept_code = Lead.objects.get(pk=self.lead_id).sub_department.code
                except (Lead.DoesNotExist, AttributeError):
                    pass
            self.sr_no = f"SR-{dept_code}-{year}{month:02d}-{seq:04d}"
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.sr_no


class SampleRequisiteItem(models.Model):
    sample_requisite = models.ForeignKey(
        SampleRequisite,
        on_delete=models.CASCADE,
        related_name='items'
    )
    stock_item  = models.ForeignKey(
        SubDeptStockItem,
        on_delete=models.PROTECT,
        related_name='sr_items'
    )
    quantity    = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    uom         = models.CharField(max_length=20, blank=True)
    # Factory field: how much was actually sent (supports partial)
    qty_sent    = models.DecimalField(max_digits=12, decimal_places=3,
                                      null=True, blank=True,
                                      help_text="Quantity actually sent by factory")
    notes       = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.stock_item.product_name} × {self.quantity}"


# ─────────────────────────────────────────────────────────────────────────────
# 5–8. Application Area models (for "Applications" type leads)
# ─────────────────────────────────────────────────────────────────────────────

class ApplicationArea(models.Model):
    """
    e.g. Kitchen, Bathroom, Terrace …
    Belongs to a specific sub-department (usually the 'Applications' sub-dept).
    """
    sub_department = models.ForeignKey(
        LeadSubDepartment,
        on_delete=models.CASCADE,
        related_name='application_areas'
    )
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('sub_department', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sub_department.code})"


class ApplicationSystemProduct(models.Model):
    """
    A named system product (batch) for a specific application area.
    e.g. "Full Bathroom Waterproofing Pack"
    """
    application_area = models.ForeignKey(
        ApplicationArea,
        on_delete=models.CASCADE,
        related_name='system_products'
    )
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('application_area', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} [{self.application_area.name}]"


class ApplicationSystemProductItem(models.Model):
    """
    Items that make up a system product.
    Can point to an existing SubDeptStockItem OR be a free-text product.
    """
    system_product  = models.ForeignKey(
        ApplicationSystemProduct,
        on_delete=models.CASCADE,
        related_name='items'
    )
    # Either link to catalogue item …
    stock_item = models.ForeignKey(
        SubDeptStockItem,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='system_product_items'
    )
    # … or provide ad-hoc details
    product_name = models.CharField(max_length=255, blank=True,
                                    help_text="Used when stock_item is not linked")
    hsn_code     = models.CharField(max_length=20, blank=True, null=True)
    rate         = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    uom          = models.CharField(max_length=20, blank=True)

    quantity     = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    is_active    = models.BooleanField(default=True)

    def get_product_name(self):
        return self.stock_item.product_name if self.stock_item else self.product_name

    def __str__(self):
        return f"{self.get_product_name()} × {self.quantity} [{self.system_product.name}]"


class ApplicationFixedItem(models.Model):
    """
    Fixed items always included for a given application area.
    """
    application_area = models.ForeignKey(
        ApplicationArea,
        on_delete=models.CASCADE,
        related_name='fixed_items'
    )
    stock_item   = models.ForeignKey(
        SubDeptStockItem,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fixed_items'
    )
    product_name = models.CharField(max_length=255, blank=True)
    hsn_code     = models.CharField(max_length=20, blank=True, null=True)
    rate         = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    uom          = models.CharField(max_length=20, blank=True)

    quantity     = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    is_active    = models.BooleanField(default=True)

    def get_product_name(self):
        return self.stock_item.product_name if self.stock_item else self.product_name

    def __str__(self):
        return f"{self.get_product_name()} [Fixed - {self.application_area.name}]"


# ─────────────────────────────────────────────────────────────────────────────
# 9. ApplicationLead  (Applications-type lead, extends Lead)
# ─────────────────────────────────────────────────────────────────────────────

class ApplicationLead(models.Model):
    """
    Extra data attached to a Lead when the lead type is 'Applications'.
    Stores which application area and which system products were selected.
    Quotation / SR flow is the same as a normal Lead.
    """
    lead             = models.OneToOneField(
        Lead,
        on_delete=models.CASCADE,
        related_name='application_detail'
    )
    application_area = models.ForeignKey(
        ApplicationArea,
        on_delete=models.PROTECT,
        related_name='app_leads'
    )
    # Selected system products (many-to-many)
    selected_system_products = models.ManyToManyField(
        ApplicationSystemProduct,
        blank=True,
        related_name='app_leads'
    )
    notes     = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AppLead for {self.lead}"
