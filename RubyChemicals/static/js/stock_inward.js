let csrf, endpoints, stockItems = [], vendors = [], vendorInwards = [];

function init(csrfToken, eps) {
    csrf = csrfToken;
    endpoints = eps;
    loadStockItems();
    loadVendors();
    loadVendorInwards();
}

async function loadStockItems() {
    const [ok, res] = await callApi("GET", endpoints.stockItems);
    if (ok && res.data) {
        stockItems = res.data;
    }
}

async function loadVendors() {
    const [ok, res] = await callApi("GET", endpoints.vendors);
    if (ok && res.data) {
        vendors = res.data;
        populateVendorSelect();
    }
}

function populateVendorSelect() {
    const select = document.getElementById("createInwardVendor");
    if (select) {
        select.innerHTML = '<option value="">Select a vendor</option>' +
            vendors.map(v => `<option value="${v.id}">${v.company_name}</option>`).join("");
    }
}

async function loadVendorInwards() {
    const [ok, res] = await callApi("GET", endpoints.vendorInwards);
    if (ok && res.data) {
        vendorInwards = res.data;
        renderVendorInwards();
    }
}

function renderVendorInwards() {
    const table = document.getElementById("vendorInwardsTable");
    
    if (!table) return;
    
    if (vendorInwards.length === 0) {
        table.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No inward entries</td></tr>';
        return;
    }

    table.innerHTML = vendorInwards.map(inward => `
        <tr>
            <td><strong style="color: #3b82f6; font-family: 'Courier New';">${inward.inward_code}</strong></td>
            <td>${inward.inward_date}</td>
            <td><strong>${inward.vendor_name || 'N/A'}</strong></td>
            <td>${inward.item_count || 0} items</td>
            <td>
                ${inward.accounted 
                    ? '<span style="background: #dcfce7; color: #15803d; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem;">✓ Yes</span>' 
                    : '<span style="background: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem;">✗ No</span>'}
            </td>
            <td>${inward.notes || ''}</td>
            <td>
                <div style="display: flex; gap: 0.5rem;">
                    <button class="btn btn-sm btn-info" onclick="viewInward(${inward.id})" title="View">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-warning" onclick="editInward(${inward.id})" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteInward(${inward.id})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join("");
}

async function openCreateInwardModal() {
    currentInwardId = null;
    document.getElementById("createInwardVendor").value = "";
    document.getElementById("createInwardDate").valueAsDate = new Date();
    document.getElementById("createInwardNotes").value = "";
    document.getElementById("createInwardAccounted").checked = false;
    document.getElementById("createInwardItems").innerHTML = 
        '<div class="text-center text-muted" style="padding: 1.5rem;"><p>No items added. Click "Add Item" to add stock items.</p></div>';
    
    inwardItems = [];
    
    const modal = new bootstrap.Modal(document.getElementById("createInwardModal"));
    modal.show();
}

function openAddInwardItemModal() {
    const vendorId = document.getElementById("createInwardVendor").value;
    if (!vendorId) {
        alert("Please select a vendor first");
        return;
    }
    
    document.getElementById("addInwardItemStockItem").innerHTML = '<option value="">Select item</option>' +
        stockItems.map(i => `<option value="${i.id}">${i.name}</option>`).join("");
    document.getElementById("addInwardItemQty").value = "";
    document.getElementById("addInwardItemNotes").value = "";
    
    const modal = new bootstrap.Modal(document.getElementById("addInwardItemModal"));
    modal.show();
}

function addInwardItem() {
    const itemId = parseInt(document.getElementById("addInwardItemStockItem").value);
    const qty = parseFloat(document.getElementById("addInwardItemQty").value);
    const notes = document.getElementById("addInwardItemNotes").value;

    if (!itemId || !qty || qty <= 0) {
        alert("Please enter valid item and quantity");
        return;
    }

    const item = stockItems.find(i => i.id === itemId);
    if (!item) {
        alert("Item not found");
        return;
    }

    inwardItems.push({ stock_item_id: itemId, quantity: qty, notes: notes, item_name: item.name });
    renderInwardItems();
    bootstrap.Modal.getInstance(document.getElementById("addInwardItemModal")).hide();
}

function renderInwardItems() {
    const container = document.getElementById("createInwardItems");
    
    if (inwardItems.length === 0) {
        container.innerHTML = '<div class="text-center text-muted" style="padding: 1.5rem;"><p>No items added. Click "Add Item" to add stock items.</p></div>';
        return;
    }

    container.innerHTML = inwardItems.map((item, idx) => `
        <div class="item-row">
            <div class="item-info">
                <div class="item-name">${item.item_name}</div>
                <div class="item-qty">Quantity: ${item.quantity}</div>
                ${item.notes ? '<div class="item-qty" style="color: #3b82f6;">Notes: ' + item.notes + '</div>' : ''}
            </div>
            <button class="btn btn-sm btn-danger" onclick="removeInwardItem(${idx})">Remove</button>
        </div>
    `).join("");
}

function removeInwardItem(idx) {
    inwardItems.splice(idx, 1);
    renderInwardItems();
}

async function submitInward() {
    const vendorId = parseInt(document.getElementById("createInwardVendor").value);
    const inwardDate = document.getElementById("createInwardDate").value;
    const notes = document.getElementById("createInwardNotes").value;
    const accounted = document.getElementById("createInwardAccounted").checked;

    if (!vendorId || !inwardDate || inwardItems.length === 0) {
        alert("Please fill all required fields and add at least one item");
        return;
    }

    const payload = {
        inward_date: inwardDate,
        vendor: vendorId,
        accounted: accounted,
        notes: notes,
        items: inwardItems
    };

    const [ok, res] = await callApi("POST", endpoints.vendorInwards, payload, csrf);
    
    if (ok) {
        bootstrap.Modal.getInstance(document.getElementById("createInwardModal")).hide();
        loadVendorInwards();
    } else {
        alert("Error creating inward: " + JSON.stringify(res.error || res));
    }
}

async function viewInward(inwardId) {
    const [ok, res] = await callApi("GET", endpoints.vendorInwards + inwardId + "/");
    
    if (ok && res.data) {
        const inward = res.data;
        
        document.getElementById("viewInwardCode").textContent = inward.inward_code;
        document.getElementById("viewInwardDate").textContent = inward.inward_date;
        document.getElementById("viewInwardVendor").textContent = inward.vendor_name || 'N/A';
        document.getElementById("viewInwardAccounted").textContent = inward.accounted ? 'Yes' : 'No';
        document.getElementById("viewInwardNotes").value = inward.notes || '';

        if (inward.items && inward.items.length > 0) {
            let itemsHtml = '';
            inward.items.forEach(item => {
                itemsHtml += `
                    <div class="item-row">
                        <div class="item-info">
                            <div class="item-name">${item.stock_item_name}</div>
                            <div class="item-qty">Quantity: ${item.quantity}</div>
                            ${item.notes ? '<div class="item-qty" style="color: #3b82f6;">Notes: ' + item.notes + '</div>' : ''}
                        </div>
                    </div>
                `;
            });
            document.getElementById("viewInwardItems").innerHTML = itemsHtml;
        } else {
            document.getElementById("viewInwardItems").innerHTML = '<p class="text-muted">No items</p>';
        }

        const modal = new bootstrap.Modal(document.getElementById("viewInwardModal"));
        modal.show();
    } else {
        alert("Error loading inward details");
    }
}

async function deleteInward(inwardId) {
    if (confirm("Are you sure you want to delete this inward entry?")) {
        const [ok, res] = await callApi("DELETE", endpoints.vendorInwards + inwardId + "/", null, csrf);
        
        if (ok) {
            loadVendorInwards();
        } else {
            alert("Error deleting inward");
        }
    }
}

let inwardItems = [];
let currentInwardId = null;
