// Copyright (c) 2025, KCSC and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lease Contract', {
    refresh: function(frm) {
        calculate_all_amounts(frm);
        calculate_totals(frm);

        if (frm.doc.docstatus === 1 && frm.doc.status !== "Terminated" && frm.doc.status !== "Renewal") {
            frm.add_custom_button(__('Renewal'), function() {
                frappe.call({
                    doc: frm.doc,
                    method: "renew_lease",
                    callback: function(r) {
                        if (!r.exc) {
                            frm.reload_doc();
                            
                            setTimeout(function() {
                                frappe.new_doc("Lease Contract", {
                                    renewed_from: frm.doc.name,
                                    tenant_lessee: frm.doc.tenant_lessee,
                                    property: frm.doc.property,
                                    floor: frm.doc.floor
                                });
                            }, 500);
                        }
                    }
                });
            }, __("Manage"));
        }

        if (frm.doc.docstatus === 1 && frm.doc.status === "Rent") {
            frm.add_custom_button(__('Terminate'), function() {
                frappe.confirm(
                    __('Are you sure you want to terminate this lease contract? This action cannot be undone.'),
                    function() {
                        frappe.call({
                            doc: frm.doc,
                            method: "terminate_lease",
                            callback: function(r) {
                                if (!r.exc) {
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __("Manage"));
        }
    },

    validate: function(frm) {
        calculate_all_amounts(frm);
        calculate_totals(frm);
    },

    rent_details: function(frm, cdt, cdn) {
        let child = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'amount', 0);
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Lease Contract Details', {
    area: function(frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
        calculate_totals(frm);
    },
    rate: function(frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
    },
    rent_item: function(frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
        calculate_totals(frm);
    },
    rent_details_remove: function(frm) {
        calculate_totals(frm);
    }
});

function calculate_all_amounts(frm) {
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
        frappe.model.set_value(cdt, cdn, 'amount', flt(child.rate));
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
    property: function (frm) {
        filter_rent_details(frm);
    },
    refresh: function (frm) {
        filter_rent_details(frm);
    },
    onload: function (frm) {
        filter_rent_details(frm);
    }
});

function filter_rent_details(frm) {
    const grid = frm.fields_dict.rent_details.grid;
    const floor_unit_field = grid.get_field("floor_unit");
    if (!floor_unit_field.hasOwnProperty('original_get_query')) {
        floor_unit_field.original_get_query = floor_unit_field.get_query;
    }
    
    floor_unit_field.get_query = function() {
        if (frm.doc.docstatus === 0 && frm.doc.property) {
            return {
                filters: {
                    property: frm.doc.property,
                    docstatus: 1,
                    disabled: 0,
                    // rent_space: 1,
                    floor: frm.doc.floor || null
                }
            };
        }
        return { filters: { name: "" } };
    };
}

frappe.ui.form.on('Lease Contract', {
    setup: function (frm) {
        frm.set_query("floor", function () {
            if (!frm.doc.property) {
                frappe.msgprint(__('Please select a Property first.'));
                return { filters: { name: "" } };
            }
            return {
                filters: {
                    property: frm.doc.property,
                    disable: 0,
                    docstatus: 1
                }
            };
        });
    },

    property: function (frm) {
        frm.refresh_field("floor");
    }
});
