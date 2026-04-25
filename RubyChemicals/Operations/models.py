from django.db import models
from django.utils import timezone


# Create your models here.
class StockGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class StockItem(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('pcs', 'Pieces'),
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
    created_at = models.DateTimeField(auto_now_add=True)

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
    created_at = models.DateTimeField(auto_now_add=True)
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
    
    created_at = models.DateTimeField(auto_now_add=True)
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
    
    created_at = models.DateTimeField(auto_now_add=True)
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
    pdf = models.FileField(upload_to='inward_pdfs/', blank=True, null=True, help_text="Invoice/Inward PDF")
    
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
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
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Adjustment - {self.stock_item.name}"

class ProductionCard(models.Model):
    production_code = models.CharField(max_length=20, unique=True)
    production_date = models.DateField()
    product_name = models.CharField(max_length=255, blank=True)
    
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
    created_at = models.DateTimeField(auto_now_add=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
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
        return f"{self.stock_item.name} - {self.production_card.production_code}"


# Petty Cash Models
class PettyCashAccount(models.Model):
    CASH_TYPE_CHOICES = [
        ('office', 'Office'),
        ('factory', 'Factory'),
    ]
    
    cash_type = models.CharField(max_length=20, choices=CASH_TYPE_CHOICES, unique=True)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Petty Cash - {self.get_cash_type_display()}"

class ExpenseHead(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class PettyCash(models.Model):
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
    
    created_by = models.ForeignKey(
        'UserDetail.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.cash_account.get_cash_type_display()} - {self.expense_head.name} - {self.amount}"


class ClientProfile(models.Model):
    company_name = models.CharField(max_length=200, unique=True)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    gst_no = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
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
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.client.company_name} - {self.address_type}"

class Dispatch(models.Model):
    dispatch_code = models.CharField(max_length=20, unique=True, editable=False)
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
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.dispatch_code:
            # Generate auto dispatch code
            from django.db.models import F
            last_dispatch = Dispatch.objects.filter(
                created_at__year=timezone.now().year
            ).order_by('-id').first()
            
            year = timezone.now().year % 100
            month = timezone.now().month
            sequence = 1 if not last_dispatch else int(last_dispatch.dispatch_code.split('-')[-1]) + 1
            self.dispatch_code = f"DISP-{year}{month:02d}-{sequence:05d}"
        
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
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.stock_item.name} - {self.quantity} {self.unit}"

