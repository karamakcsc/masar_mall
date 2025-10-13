// Copyright (c) 2025, KCSC and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lease Contract', {
    refresh: function (frm) {
        create_custom_buttons(frm);
        filter_rent_details(frm);
        calculate_totals(frm);
    },

    validate: function (frm) {
        calculate_totals(frm);
    },

    rent_details: function (frm, cdt, cdn) {
        calculate_totals(frm);
    },

    setup: function (frm) {
        filter_floor(frm);
    },

    onload: function (frm) {
        filter_rent_details(frm);
    },

    property: function (frm) {
        filter_rent_details(frm);
        frm.refresh_field("floor");
    }
});

frappe.ui.form.on('Lease Contract Details', {
    rate: function (frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
        recalculate_service_items(frm);
    },

    amount: function (frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
        recalculate_service_items(frm);
    },

    rent_item: function (frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
        recalculate_service_items(frm);
        calculate_totals(frm);
    },

    rent_details_remove: function (frm) {
        calculate_totals(frm);
    }
});

function calculate_row_amount(frm, cdt, cdn) {
    const child = locals[cdt][cdn];
    if (!child.rent_item) return;

    const is_stock_item = child.is_stock_item;
    const service_percentage = flt(child.custom_service_percentage);
    let amount = 0;

    if (is_stock_item) {
        amount = flt(child.rate);
    } else {
        if (service_percentage > 0) {
            const total_stock_amount = get_total_stock_amount(frm);
            amount = (service_percentage / 100) * total_stock_amount;
        } else {
            amount = flt(child.rate);
        }
    }

    frappe.model.set_value(cdt, cdn, "rate", amount);
    frappe.model.set_value(cdt, cdn, "amount", amount);
}

function get_total_stock_amount(frm) {
    let total = 0;
    (frm.doc.rent_details || []).forEach(row => {
        if (row.is_stock_item) {
            total += flt(row.amount);
        }
    });
    return total;
}

function recalculate_service_items(frm) {
    const total_stock_amount = get_total_stock_amount(frm);

    (frm.doc.rent_details || []).forEach(row => {
        if (!row.is_stock_item && flt(row.custom_service_percentage) > 0) {
            const new_amount = (flt(row.custom_service_percentage) / 100) * total_stock_amount;
            frappe.model.set_value(row.doctype, row.name, "rate", new_amount);
            frappe.model.set_value(row.doctype, row.name, "amount", new_amount);
        }
    });
}

function get_total_stock_amount(frm) {
    let total = 0;
    (frm.doc.rent_details || []).forEach(row => {
        if (row.is_stock_item) {
            total += flt(row.amount);
        }
    });
    return total;
}

function recalculate_service_items(frm) {
    (frm.doc.rent_details || []).forEach(row => {
        if (row.rent_item && !row.is_stock_item) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Item",
                    filters: { name: row.rent_item },
                    fieldname: ["custom_service_percentage"]
                },
                callback: function(r) {
                    if (!r.message) return;
                    let percentage = flt(r.message.custom_service_percentage);
                    if (percentage > 0) {
                        let total_stock = get_total_stock_amount(frm);
                        let new_amount = (percentage / 100) * total_stock;
                        frappe.model.set_value(row.doctype, row.name, "rate", new_amount);
                        frappe.model.set_value(row.doctype, row.name, "amount", new_amount);
                    }
                }
            });
        }
    });
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

function filter_rent_details(frm) {
    const grid = frm.fields_dict.rent_details.grid;
    const floor_unit_field = grid.get_field("floor_unit");

    if (!floor_unit_field.hasOwnProperty('original_get_query')) {
        floor_unit_field.original_get_query = floor_unit_field.get_query;
    }

    floor_unit_field.get_query = function () {
        if (frm.doc.docstatus === 0 && frm.doc.property) {
            return {
                filters: {
                    property: frm.doc.property,
                    docstatus: 1,
                    disabled: 0,
                    floor: frm.doc.floor || null
                }
            };
        }
        return { filters: { name: "" } };
    };
}

function filter_floor(frm) {
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
}

function create_custom_buttons(frm) {
    if (frm.doc.docstatus === 1 && frm.doc.status === "Rent") {

        frm.add_custom_button(__('Renewal'), function () {
            let renewed_from = frm.doc.name;

            setTimeout(function () {
                frappe.new_doc("Lease Contract", {
                    renewed_from: renewed_from,
                    tenant_lessee: frm.doc.tenant_lessee,
                    property: frm.doc.property,
                    floor: frm.doc.floor,
                    represented_by: frm.doc.represented_by,
                    rent_details: frm.doc.rent_details,
                    lease_start: frm.doc.lease_end,
                    lease_end: null,
                    billing_frequency: frm.doc.billing_frequency,
                    allowance_period: frm.doc.allowance_period,
                    in_periodic: frm.doc.in_periodic,
                    out_periodic: frm.doc.out_periodic,
                    accommodation_type: frm.doc.accommodation_type,
                });
            }, 500);
        }, __("Manage"));

        frm.add_custom_button(__('Terminate'), function () {
            frappe.confirm(
                __('<b>Are you sure you want to terminate this lease contract? This action cannot be undone.</b>'),
                function () {
                    frappe.call({
                        doc: frm.doc,
                        method: "terminate_lease",
                        callback: function (r) {
                            if (!r.exc) frm.reload_doc();
                        }
                    });
                }
            );
        }, __("Manage"));

        frm.add_custom_button(__('Legal Case'), function () {
            frappe.confirm(
                __('<b>Are you sure you want to put a legal case for this lease contract?</b>'),
                function () {
                    frappe.call({
                        doc: frm.doc,
                        method: "legal_case",
                        callback: function (r) {
                            if (!r.exc) frm.reload_doc();
                        }
                    });
                }
            );
        }, __("Manage"));
    }
}