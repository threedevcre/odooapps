/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
const { onWillStart } = owl;

patch(WebClient.prototype, {
    setup() {
        super.setup()
        this.title.setParts({ zopenerp: "" });
    },
    async willStart() {
        // Fetch from ORM
        this.orm = useService("orm");
        const com = await this.orm.call('res.company', 'get_current_company', []);
        const args = {
            domain: [['id', '=', com]],
            fields: ["brand_name", "name"],
            context: [],
        }
        const res = await this.orm.call('res.company', 'search_read', [], args);
        this.brandName = res && res[0].brand_name;
        this.CompanyName = res && res[0].name;
        const brand_name = this.brandName || this.CompanyName;
        this.title.setParts({ zopenerp: brand_name }); // :)
    },
});

patch(Dialog.prototype,{
    setup() {
        super.setup();
        this.title = this.title && this.title.replace(new RegExp("Odoo", "g"), "");
        this.constructor.title = this.constructor.title &&  this.constructor.title.replace(new RegExp("Odoo", "g"), "");
    },
});

// Remove Odoo Caption From Title
Dialog.title  = Dialog.title && Dialog.title.replace(new RegExp("Odoo", "g"), "");

import { notificationPermissionService } from "@mail/core/common/notification_permission_service";
import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { isAndroidApp, isIosApp } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";

export const customnotificationPermissionService = {
       ...notificationPermissionService,

          async start(env, services) {
        const notification = services.notification;
        let permission;
        try {
            permission = await browser.navigator?.permissions?.query({
                name: "notifications",
            });
        } catch {
            // noop
        }
        const state = reactive({
            /** @type {"prompt" | "granted" | "denied"} */
            permission:
                isIosApp() || isAndroidApp()
                    ? "denied"
                    : this._normalizePermission(
                          permission?.state ?? browser.Notification?.permission
                      ),
            requestPermission: async () => {
                if (browser.Notification && state.permission === "prompt") {
                    state.permission = this._normalizePermission(
                        await browser.Notification.requestPermission()
                    );
                    if (state.permission === "denied") {
                        notification.add(_t("System will not send notifications on this device."), {
                            type: "warning",
                            title: _t("Notifications blocked"),
                        });
                    } else if (state.permission === "granted") {
                        notification.add(_t("System will send notifications on this device!"), {
                            type: "success",
                            title: _t("Notifications allowed"),
                        });
                    }
                }
            },
        });
        if (permission) {
            permission.addEventListener("change", () => (state.permission = permission.state));
        }
        return state;
    },

}