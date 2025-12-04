// Copyright (c) 2025, KCSC and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lease Contract', {
    refresh: function (frm) {
        filter_tax(frm);
        create_custom_buttons(frm);
        filter_rent_details(frm);
        calculate_totals(frm);
        if (frm.doc.__islocal != 1) {
            frm.set_df_property("rent_schedule", "options", generate_rent_schedule_html(frm));
            frm.refresh_field("rent_schedule");
        }
    },

    validate: function (frm) {
        calculate_totals(frm);
        totalQuantityAndService(frm);
        if (frm.doc.__islocal != 1) {
            frm.set_df_property("rent_schedule", "options", generate_rent_schedule_html(frm));
            frm.refresh_field("rent_schedule");
        }
    },

    rent_details: function (frm) {
        calculate_totals(frm);
    },

    setup: function (frm) {
        filter_tax(frm);
        filter_floor(frm);
    },

    onload: function (frm) {
        filter_tax(frm);
        filter_rent_details(frm);
    },

    property: function (frm) {
        filter_rent_details(frm);
        frm.refresh_field("floor");
    },

    owner_lessor: function (frm) {
        filter_tax(frm);
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
    },
   
});

frappe.ui.form.on("Lease Contract Period Details", {
    from_date: function (frm, cdt, cdn) {
        calculate_period(frm, cdt, cdn);
    },
    to_date: function (frm, cdt, cdn) {
        calculate_period(frm, cdt, cdn);
    },
    space_amount: function (frm, cdt, cdn) {
        calc_amount(frm, cdt, cdn);
    },
    service_amount: function (frm, cdt, cdn) {
        calc_amount(frm, cdt, cdn);
    }
});

function calculate_row_amount(frm, cdt, cdn) {
    const child = locals[cdt][cdn];
    if (!child.rent_item) return;

    const is_stock_item = child.is_stock_item;
    const service_percentage = flt(child.service_percentage);
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
        if (!row.is_stock_item && flt(row.service_percentage) > 0) {
            const new_amount = (flt(row.service_percentage) / 100) * total_stock_amount;
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

function filter_tax(frm) {
    frm.set_query("tax_template", function () {
        if (!frm.doc.owner_lessor) {
            frappe.msgprint(__('Please select a Company first.'));
            return { filters: { name: "" } };
        }

        return {
            filters: {
                company: frm.doc.owner_lessor,
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

/**
 * Updated generate_rent_schedule_html function with preview support
 */
function generate_rent_schedule_html(frm) {
    frm.fields_dict['rent_schedule'].html("<p>Loading rent schedule...</p>");

    // For draft documents, generate preview
    if (frm.doc.docstatus === 0) {
        if (!frm.doc.lease_start || !frm.doc.lease_end || !frm.doc.billing_frequency) {
            frm.fields_dict['rent_schedule'].html(
                "<p style='color:orange;'>Please set Lease Start Date, Lease End Date, and Billing Frequency to preview the schedule.</p>"
            );
            return;
        }

        frappe.call({
            method: "generate_schedule_preview",
            doc: frm.doc,
            callback: function (response) {
                if (response.message) {
                    render_schedule_table(frm, response.message, true);
                } else {
                    frm.fields_dict['rent_schedule'].html(
                        "<p style='color:red;'>Error generating preview. Please check your data.</p>"
                    );
                }
            },
            error: function(err) {
                frm.fields_dict['rent_schedule'].html(
                    "<p style='color:red;'>Error: " + (err.message || "Failed to generate preview") + "</p>"
                );
            }
        });
        return;
    }

    // For submitted documents, load actual schedule
    if (!frm.doc.name) {
        frm.fields_dict['rent_schedule'].html(
            "<p style='color:red;'>Lease Contract must be saved before loading schedule.</p>"
        );
        return;
    }

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Lease Contract Schedule",
            filters: { 
                lease_contract: frm.doc.name,
                docstatus: 1
            },
            fields: ["name"],
            limit_page_length: 1
        },
        callback: function (response) {
            if (!response.message || response.message.length === 0) {
                frm.fields_dict['rent_schedule'].html(
                    "<p style='color:orange;'>No Lease Contract Schedule found for this contract.</p>"
                );
                return;
            }

            const scheduleName = response.message[0].name;

            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Lease Contract Schedule",
                    name: scheduleName
                },
                callback: function (scheduleResponse) {
                    const leaseSchedule = scheduleResponse.message || {};
                    render_schedule_table(frm, leaseSchedule, false);
                }
            });
        }
    });
}

/**
 * Render the schedule table from schedule data
 * @param {object} frm - The Frappe form object
 * @param {object} scheduleData - The schedule data object with invoice array
 * @param {boolean} isPreview - Whether this is a preview or actual schedule
 */
function render_schedule_table(frm, scheduleData, isPreview) {
    let invoiceList = scheduleData.invoice || [];

    if (!invoiceList.length) {
        frm.fields_dict['rent_schedule'].html(
            "<p style='color:orange;'>Schedule has no invoice rows.</p>"
        );
        return;
    }

    // Sort by lease_start date
    invoiceList = invoiceList.slice().sort(function(invoiceA, invoiceB) {
        const startDateA = invoiceA.lease_start ? new Date(invoiceA.lease_start) : new Date(0);
        const startDateB = invoiceB.lease_start ? new Date(invoiceB.lease_start) : new Date(0);
        return startDateA - startDateB;
    });

    /**
     * @param {string|Date} dateString
     * @returns {string}
     */
    function formatDate(dateString) {
        if (!dateString) return "";
        const date = new Date(dateString);
        if (isNaN(date)) return String(dateString).slice(0, 10);
        return date.toISOString().slice(0, 10);
    }

    /**
     * @param {number} amount
     * @returns {string}
     */
    function formatCurrency(amount) {
        return amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    /**
     * @param {number} currentIndex
     * @returns {string}
     */
    function calculatePeriodEndDate(currentIndex) {
        const currentInvoice = invoiceList[currentIndex];
        
        if (currentInvoice.lease_end) {
            return formatDate(currentInvoice.lease_end);
        }

        if (currentIndex < invoiceList.length - 1 && invoiceList[currentIndex + 1].lease_start) {
            const nextPeriodStart = new Date(invoiceList[currentIndex + 1].lease_start);
            nextPeriodStart.setDate(nextPeriodStart.getDate() - 1);
            return formatDate(nextPeriodStart);
        }

        if (currentInvoice.lease_start) {
            const startDate = new Date(currentInvoice.lease_start);
            const lastDayOfMonth = new Date(startDate.getFullYear(), startDate.getMonth() + 1, 0);
            return formatDate(lastDayOfMonth);
        }

        return "";
    }

    let cumulativeTotal = 0;
    
    let previewBanner = isPreview ? `
        <div style="background-color: #fff3cd; border: 1px solid #ffc107; padding: 10px; margin-bottom: 10px; border-radius: 4px;">
            This is a preview of the schedule. Submit the document to create the actual schedule.
        </div>` : '';
    
    let htmlTable = previewBanner + `
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width:100%;">
            <tr style="background-color:#f2f2f2; text-align:center;">
                <th>Row #</th>
                <th>Month Start</th>
                <th>Month End</th>
                <th>Amount</th>
                <th>Total Accumulated</th>
            </tr>`;

    invoiceList.forEach((currentInvoice, rowIndex) => {
        const periodStartDate = formatDate(currentInvoice.lease_start);
        const periodEndDate = calculatePeriodEndDate(rowIndex);
        const invoiceAmount = parseFloat(currentInvoice.amount || 0);
        cumulativeTotal += invoiceAmount;

        const isAllowance = currentInvoice.is_allowance;
        const amountDisplay = isAllowance ? 
            `<span>Free Period</span>` : 
            formatCurrency(invoiceAmount);

        htmlTable += `
            <tr style="text-align:center;">
                <td>${rowIndex + 1}</td>
                <td>${periodStartDate}</td>
                <td>${periodEndDate}</td>
                <td>${amountDisplay}</td>
                <td>${formatCurrency(cumulativeTotal)}</td>
            </tr>`;
    });

    htmlTable += `
    </table>`;

    frm.fields_dict['rent_schedule'].html(htmlTable);
}

function totalQuantityAndService(frm){
    let total_qty = 0;
    let total_service = 0;

    (frm.doc.other_service || []).forEach(row => {
        const amt = flt(row.rate || 0);
        // make rate equal to amount
        frappe.model.set_value(row.doctype, row.name, 'amount', amt);

        total_qty += 1;
        total_service += amt;
    });

    frm.set_value('total_quantity', total_qty);
    frm.set_value('total_service', total_service);
    frm.refresh_field('other_service');
}

function calculate_period(frm, cdt, cdn) {
    var child = locals[cdt][cdn];
    if (child.from_date && child.to_date) {
        const start = new Date(child.from_date);
        const end = new Date(child.to_date);
        const months = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth()) + 1;
        frappe.model.set_value(cdt, cdn, "month_in_period", months);
    } else {
        frappe.model.set_value(cdt, cdn, "month_in_period", 0);
    }
}

function calc_amount(frm, cdt, cdn) {
    var child = locals[cdt][cdn];
    if (child.space_amount && child.service_amount) {
        const amount = flt(child.space_amount) + flt(child.service_amount);
        frappe.model.set_value(cdt, cdn, "amount", amount);
    } else {
        frappe.model.set_value(cdt, cdn, "amount", 0);
    }
}