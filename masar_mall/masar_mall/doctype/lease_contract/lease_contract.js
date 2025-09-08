// Copyright (c) 2025, KCSC and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lease Contract', {
    refresh: function(frm) {
        // Initialize calculations when form loads
        calculate_all_amounts(frm);
        calculate_totals(frm);
    },
    validate: function(frm) {
        // Recalculate everything before saving
        calculate_all_amounts(frm);
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Rent Details', {
    area: function(frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
        calculate_totals(frm);
    },
    rate: function(frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
        calculate_totals(frm);
    },
    rent_details_remove: function(frm) {
        calculate_totals(frm);
    },
    rent_details_add: function(frm, cdt, cdn) {
        // Initialize new row
        let child = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'amount', 0);
        calculate_totals(frm);
    }
});

// ---- CALCULATION FUNCTIONS ----

function calculate_all_amounts(frm) {
    // Recalculate amounts for all rows
    if (frm.doc.rent_details) {
        frm.doc.rent_details.forEach(function(row) {
            if (row.rent_space == 1) {
                row.amount = row.area * row.rate;
            } else {
                row.amount = row.rate;
            }
        });
    }
}

function calculate_row_amount(frm, cdt, cdn) {
    let child = locals[cdt][cdn];
    if (child.area !== undefined && child.rate !== undefined) {
        let amount = flt(child.area) * flt(child.rate);
        frappe.model.set_value(cdt, cdn, 'amount', amount);
    } else {
        frappe.model.set_value(cdt, cdn, 'amount', child.rate);
    }
}

function calculate_totals(frm) {
    let total_elements = 0;
    let total_amount = 0;

    if (frm.doc.rent_details) {
        frm.doc.rent_details.forEach(row => {
            if (row.amount !== undefined) {
                total_elements++;
                total_amount += flt(row.amount);
            }
        });
    }

    frm.set_value("total_rent_elements", total_elements);
    frm.set_value("total_rent_amount", total_amount);
    frm.refresh_field("total_rent_elements");
    frm.refresh_field("total_rent_amount");
}

frappe.ui.form.on('Lease Contract', {
   refresh: function(frm) {
       frm.add_custom_button(__('Renewal'), function() {
            let newDoc = frappe.model.copy_doc(frm.doc);
            frappe.set_route('Form', newDoc.doctype, newDoc.name);
       }, __("Manage"));

       frm.add_custom_button(__('Stop'), function() {
            frm.set_value('is_stopped', 1);
            frm.set_df_property('is_stopped', 'hidden', 0); // Show the field
            frm.save();
            frappe.msgprint(__('Contract stopped. No further invoices will be created.'));
       }, __("Manage"));

       // Always hide the field on refresh unless stopped
       if (!frm.doc.is_stopped) {
            frm.set_df_property('is_stopped', 'hidden', 1);
       }
    }
});