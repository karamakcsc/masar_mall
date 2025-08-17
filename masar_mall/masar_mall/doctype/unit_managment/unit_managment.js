// Copyright (c) 2025, KCSC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Unit Managment", {
    setup: function (frm) {
        const requireProperty = () => {
            if (!frm.doc.property) {
                frappe.msgprint(__('Please select a Property first.'));
                return false;
            }
            return true;
        };
        frm.set_query("return_exit_unit", function () {
            if (!requireProperty()) return { filters: { name: "" } };
            return {
                filters: {
                    property: frm.doc.property,
                    floor: frm.doc.floor,
                    disable: 0,
                    docstatus: 1,
                    return_space: 0,
                    rent_space: 1
                }
            };
        });
        frm.set_query("floor", function () {
            if (!requireProperty()) return { filters: { name: "" } };
            return {
                filters: {
                    property: frm.doc.property,
                    disable: 0,
                    docstatus: 1
                }
            };
        });
        frm.set_query("rent_exist_unit", function () {
            if (!requireProperty()) return { filters: { name: "" } };
            return {
                filters: {
                    property: frm.doc.property,
                    floor: frm.doc.floor,
                    disable: 0,
                    docstatus: 1,
                    rent_space: 1
                }
            };
        });
    },
    property: function (frm) {
        frm.refresh_field("return_exit_unit");
        frm.refresh_field("floor");
        frm.refresh_field("rent_exist_unit");
    }
});
