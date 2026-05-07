const ADMIN_DASHBOARD_API = "/operation-api/admin-dashboard-api/";
const ADMIN_MARK_ACCOUNTED_API = "/operation-api/admin-dashboard-api/mark_accounted/";
const ADMIN_MARK_DISPATCH_ACCOUNTED_API = "/operation-api/admin-dashboard-api/mark_dispatch_accounted/";
const MARK_DISPATCH_ACCOUNTED_API = "/operation-api/mark-dispatch-accounted-api/";
const MARK_VENDOR_INWARD_ACCOUNTED_API = "/operation-api/mark-vendor-inward-accounted-api/";
const STOCK_ITEM_API = "/operation-api/stock-item-api/";
const STOCK_GROUP_API = "/operation-api/stock-group-api/";
let csrf_token = ""
let stockGroups = [];
let currentCardId = null;
let currentDispatchId = null;
let currentInwardId = null;
let unaccountedCards = [];
let pendingDispatches = [];
let pendingInwards = [];

async function loadAdminDashboard(csrf_token_param) {
    csrf_token = csrf_token_param
    const [ok, res] = await callApi("GET", ADMIN_DASHBOARD_API);
    if (ok && res.data) {
        const data = res.data;
        unaccountedCards = data.unaccounted_cards;
        pendingDispatches = data.pending_dispatches || [];
        pendingInwards = data.pending_inwards || [];
        
        document.getElementById("negativeStockCount").textContent = data.negative_stock_count;
        document.getElementById("lowStockCount").textContent = data.low_stock_items.length;
        document.getElementById("totalItemsCount").textContent = data.total_items;
        document.getElementById("totalGroupsCount").textContent = data.total_groups;
        document.getElementById("unaccountedCount").textContent = data.unaccounted_count;
        document.getElementById("recentBatchesCount").textContent = data.recent_batches.length;

        // Low/Negative Stock Table
        const lowStockTable = document.getElementById("lowStockTable");
        if (data.low_stock_items.length === 0) {
            lowStockTable.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">All items in good stock</td></tr>';
        } else {
            lowStockTable.innerHTML = data.low_stock_items.map(item => {
                let badgeClass = 'badge-warning';
                let statusText = 'Low Stock';
                if (item.current_quantity < 0) {
                    badgeClass = 'badge-critical';
                    statusText = 'CRITICAL - Negative';
                }
                return `
                    <tr style="background: ${item.current_quantity < 0 ? '#fef2f2' : '#fffbeb'};">
                        <td><strong>${item.name}</strong></td>
                        <td><span style="background: #e0e7ff; color: #3730a3; padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.85rem;">${item.group__name}</span></td>
                        <td style="font-weight: 600; color: ${item.current_quantity < 0 ? '#dc2626' : '#f97316'};"><strong>${item.current_quantity.toFixed(2)}</strong></td>
                        <td>${item.unit}</td>
                        <td><span class="badge ${badgeClass}" style="font-size: 0.8rem;">${statusText}</span></td>
                    </tr>
                `;
            }).join("");
        }

        // Unaccounted Cards Table
        const unaccountedCardsTable = document.getElementById("unaccountedCardsTable");
        if (data.unaccounted_cards.length === 0) {
            unaccountedCardsTable.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">All cards accounted</td></tr>';
        } else {
            unaccountedCardsTable.innerHTML = data.unaccounted_cards.map(card => `
                <tr>
                    <td><code style="background: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 6px; font-weight: 600;">${card.production_code}</code></td>
                    <td>${card.production_date}</td>
                    <td><strong>${card.total_output_quantity}</strong></td>
                    <td>${card.unit}</td>
                    <td><span style="background: #f3e8ff; color: #6b21a8; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem;">${card.batch_count || 0} batches</span></td>
                    <td><span style="background: #e0f2fe; color: #0c4a6e; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem;">${card.consumption_count || 0} items</span></td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="viewProductionCard(${card.id})" title="View details">
                            <i class="fas fa-eye"></i> View
                        </button>
                    </td>
                </tr>
            `).join("");
        }

        // Pending Dispatches Table
        const pendingDispatchesTable = document.getElementById("pendingDispatchesTable");
        if (!data.pending_dispatches || data.pending_dispatches.length === 0) {
            pendingDispatchesTable.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">All dispatches accounted</td></tr>';
        } else {
            pendingDispatchesTable.innerHTML = data.pending_dispatches.map(dispatch => `
                <tr>
                    <td><code style="background: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 6px; font-weight: 600;">${dispatch.dispatch_code}</code></td>
                    <td>${dispatch.dispatch_date}</td>
                    <td>${dispatch.client_name}</td>
                    <td>${dispatch.vehicle_number || 'N/A'}</td>
                    <td><span style="background: #e0e7ff; color: #3730a3; padding: 4px 8px; border-radius: 4px; font-weight: 600;">${dispatch.item_count}</span></td>
                    <td>₹${dispatch.freight_amount}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="viewDispatch(${dispatch.id})" title="View details">
                            <i class="fas fa-eye"></i> View
                        </button>
                    </td>
                </tr>
            `).join("");
        }

        // Pending Inwards Table
        const pendingInwardsTable = document.getElementById("pendingInwardsTable");
        if (!data.pending_inwards || data.pending_inwards.length === 0) {
            pendingInwardsTable.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">All inwards accounted</td></tr>';
        } else {
            pendingInwardsTable.innerHTML = data.pending_inwards.map(inward => `
                <tr>
                    <td><code style="background: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 6px; font-weight: 600;">${inward.inward_code}</code></td>
                    <td>${inward.inward_date}</td>
                    <td>${inward.vendor_name}</td>
                    <td><span style="background: #e0e7ff; color: #3730a3; padding: 4px 8px; border-radius: 4px; font-weight: 600;">${inward.item_count}</span></td>
                    <td>${inward.invoice_number}</td>
                    <td>${inward.has_pdf ? '<i class="fas fa-check text-success"></i>' : '<i class="fas fa-times text-muted"></i>'}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="viewInward(${inward.id})" title="View details">
                            <i class="fas fa-eye"></i> View
                        </button>
                    </td>
                </tr>
            `).join("");
        }

        // Recent Batches Table
        const recentBatchesTable = document.getElementById("recentBatchesTable");
        if (data.recent_batches.length === 0) {
            recentBatchesTable.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No recent batches</td></tr>';
        } else {
            recentBatchesTable.innerHTML = data.recent_batches.map(batch => `
                <tr>
                    <td><code style="background: #dbeafe; color: #1e40af; padding: 2px 6px; border-radius: 3px; font-weight: 600;">${batch.batch_code}</code></td>
                    <td><strong>${batch.production_card__production_code}</strong></td>
                    <td>${batch.product__name}</td>
                    <td><span style="background: #dcfce7; padding: 4px 8px; border-radius: 4px; color: #15803d; font-weight: 600;">${batch.output_quantity}</span></td>
                    <td><span style="background: #fee2e2; padding: 4px 8px; border-radius: 4px; color: #991b1b;">${batch.loss_quantity}</span></td>
                    <td style="color: #64748b; font-size: 0.875rem;">${batch.created_at ? new Date(batch.created_at).toLocaleDateString() : 'N/A'}</td>
                </tr>
            `).join("");
        }
    }
}

async function loadStockGroups() {
    const [ok, res] = await callApi("GET", STOCK_GROUP_API);
    if (ok && res.data) {
        stockGroups = res.data;
        const groupSelect = document.getElementById("quickAddGroup");
        groupSelect.innerHTML = '<option value="">Select a group</option>' + stockGroups.map(g => 
            `<option value="${g.id}">${g.name}</option>`
        ).join("");
    }
}

async function quickAddStockItem() {
    const name = document.getElementById("quickAddName").value;
    const groupId = document.getElementById("quickAddGroup").value;
    const unit = document.getElementById("quickAddUnit").value;
    const qty = document.getElementById("quickAddQty").value;

    if (!name || !groupId || !unit || !qty) {
        alert("Please fill all required fields");
        return;
    }

    const payload = {
        name: name,
        group: groupId,
        unit: unit,
        current_quantity: qty
    };

    const [ok, res] = await callApi("POST", STOCK_ITEM_API, payload, csrf_token);
    if (ok && res.success) {
        alert("Stock item added successfully!");
        document.getElementById("quickAddName").value = "";
        document.getElementById("quickAddGroup").value = "";
        document.getElementById("quickAddUnit").value = "";
        document.getElementById("quickAddQty").value = "";
        
        const modal = bootstrap.Modal.getInstance(document.getElementById("quickAddStockModal"));
        if (modal) modal.hide();
        
        loadAdminDashboard();
    } else {
        alert("Error: " + (res.error || "Failed to add stock item"));
    }
}

async function markAccounted(cardId) {
    if (confirm("Mark this production card as accounted?")) {
        const [ok, res] = await callApi("POST", ADMIN_MARK_ACCOUNTED_API, { card_id: cardId }, csrf_token);
        if (ok && res.success) {
            alert("Production card marked as accounted!");
            loadAdminDashboard();
        } else {
            alert("Error: " + (res.error || "Failed to update"));
        }
    }
}

function viewProductionCard(cardId) {
    const card = findCardById(cardId);
    if (!card) return;
    
    currentCardId = cardId;
    document.getElementById("viewCardCode").textContent = card.production_code;
    document.getElementById("viewCardDate").textContent = card.production_date;
    document.getElementById("viewCardOutput").textContent = card.total_output_quantity + " " + card.unit;
    document.getElementById("viewCardBatches").textContent = card.batch_count + " batches, " + card.consumption_count + " materials";
    
    new bootstrap.Modal(document.getElementById("viewProductionCardModal")).show();
}

function viewDispatch(dispatchId) {
    const dispatch = findDispatchById(dispatchId);
    if (!dispatch) return;
    
    currentDispatchId = dispatchId;
    document.getElementById("viewDispatchCode").textContent = dispatch.dispatch_code;
    document.getElementById("viewDispatchDate").textContent = dispatch.dispatch_date;
    document.getElementById("viewDispatchClient").textContent = dispatch.client_name;
    document.getElementById("viewDispatchVehicle").textContent = dispatch.vehicle_number || "N/A";
    document.getElementById("viewDispatchItems").textContent = dispatch.item_count + " items";
    document.getElementById("viewDispatchFreight").textContent = "₹" + dispatch.freight_amount;
    
    new bootstrap.Modal(document.getElementById("viewDispatchModalAdmin")).show();
}

function findCardById(cardId) {
    return unaccountedCards.find(card => card.id === cardId);
}

function findDispatchById(dispatchId) {
    return pendingDispatches.find(dispatch => dispatch.id === dispatchId);
}

async function markCardAccountedFromModal() {
    if (confirm("Mark this production card as accounted?")) {
        const [ok, res] = await callApi("POST", ADMIN_MARK_ACCOUNTED_API, { card_id: currentCardId }, csrf_token);
        if (ok && res.success) {
            alert("Production card marked as accounted!");
            const modal = bootstrap.Modal.getInstance(document.getElementById("viewProductionCardModal"));
            if (modal) modal.hide();
            loadAdminDashboard();
        } else {
            alert("Error: " + (res.error || "Failed to update"));
        }
    }
}

async function markDispatchAccountedFromModal() {
    if (confirm("Mark this dispatch as accounted?")) {
        const [ok, res] = await callApi("POST", ADMIN_MARK_DISPATCH_ACCOUNTED_API, { dispatch_id: currentDispatchId }, csrf_token);
        if (ok && res.success) {
            alert("Dispatch marked as accounted!");
            const modal = bootstrap.Modal.getInstance(document.getElementById("viewDispatchModalAdmin"));
            if (modal) modal.hide();
            loadAdminDashboard();
        } else {
            alert("Error: " + (res.error || "Failed to update"));
        }
    }
}

function openMarkDispatchAccountedModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById("viewDispatchModalAdmin"));
    if (modal) modal.hide();
    
    document.getElementById("dispatchInvoiceNumber").value = "";
    document.getElementById("dispatchPdfFile").value = "";
    new bootstrap.Modal(document.getElementById("markDispatchAccountedModal")).show();
}

async function submitMarkDispatchAccounted() {
    const invoiceNumber = document.getElementById("dispatchInvoiceNumber").value.trim();
    const pdfFile = document.getElementById("dispatchPdfFile").files[0] || null;
    
    if (!invoiceNumber) {
        alert("Invoice number is required");
        return;
    }
    
    const formData = new FormData();
    formData.append("dispatch_id", currentDispatchId);
    formData.append("invoice_number", invoiceNumber);
    if (pdfFile) {
        formData.append("pdf", pdfFile);
    }
    
    const [ok, res] = await fetch(MARK_DISPATCH_ACCOUNTED_API, {
        method: "POST",
        headers: {
            "X-CSRFToken": csrf_token
        },
        body: formData
    }).then(r => r.json()).then(data => [true, data]).catch(e => [false, {error: e.message}]);
    
    if (ok && res.success) {
        alert("Dispatch marked as accounted successfully!");
        const modal = bootstrap.Modal.getInstance(document.getElementById("markDispatchAccountedModal"));
        if (modal) modal.hide();
        loadAdminDashboard();
    } else {
        alert("Error: " + (res.error || "Failed to update"));
    }
}

function viewInward(inwardId) {
    const inward = findInwardById(inwardId);
    if (!inward) return;
    
    currentInwardId = inwardId;
    document.getElementById("viewInwardCode").textContent = inward.inward_code;
    document.getElementById("viewInwardDate").textContent = inward.inward_date;
    document.getElementById("viewInwardVendor").textContent = inward.vendor_name;
    document.getElementById("viewInwardItems").textContent = inward.item_count + " items";
    
    new bootstrap.Modal(document.getElementById("viewInwardModalAdmin")).show();
}

function openMarkInwardAccountedModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById("viewInwardModalAdmin"));
    if (modal) modal.hide();
    
    document.getElementById("inwardInvoiceNumber").value = "";
    document.getElementById("inwardInvoiceValue").value = "";
    document.getElementById("inwardPdfFile").value = "";
    new bootstrap.Modal(document.getElementById("markInwardAccountedModal")).show();
}

async function submitMarkInwardAccounted() {
    const invoiceNumber = document.getElementById("inwardInvoiceNumber").value.trim();
    const invoiceValue = document.getElementById("inwardInvoiceValue").value.trim();
    const pdfFile = document.getElementById("inwardPdfFile").files[0] || null;
    
    if (!invoiceNumber) {
        alert("Invoice number is required");
        return;
    }
    
    const formData = new FormData();
    formData.append("inward_id", currentInwardId);
    formData.append("invoice_number", invoiceNumber);
    formData.append("invoice_value", invoiceValue);
    if (pdfFile) {
        formData.append("pdf", pdfFile);
    }
    
    const [ok, res] = await fetch(MARK_VENDOR_INWARD_ACCOUNTED_API, {
        method: "POST",
        headers: {
            "X-CSRFToken": csrf_token
        },
        body: formData
    }).then(r => r.json()).then(data => [true, data]).catch(e => [false, {error: e.message}]);
    
    if (ok && res.success) {
        alert("Inward marked as accounted successfully!");
        const modal = bootstrap.Modal.getInstance(document.getElementById("markInwardAccountedModal"));
        if (modal) modal.hide();
        loadAdminDashboard();
    } else {
        alert("Error: " + (res.error || "Failed to update"));
    }
}

function findInwardById(inwardId) {
    return pendingInwards.find(inward => inward.id === inwardId);
}

