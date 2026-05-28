import requests
from collections import Counter

from plugins.base_plugin.base_plugin import BasePlugin


class PfSenseStatus(BasePlugin):
    def _get_common_config(self, device_config):
        api_base = device_config.load_env_key("PFSENSE_API_BASE") or "https://pfsense.lan"
        api_key = device_config.load_env_key("PFSENSE_API_KEY")

        verify_ssl_env = device_config.load_env_key("PFSENSE_VERIFY_SSL") or "false"
        verify_ssl = verify_ssl_env.lower() == "true"

        if not api_key:
            raise RuntimeError(
                "pfSense API key not configured. "
                "Set PFSENSE_API_KEY in the InkyPi .env."
            )

        headers = {"X-API-Key": api_key}
        auth = None

        return api_base, headers, auth, verify_ssl

    def _call_api(self, url, headers, auth, verify_ssl, timeout=10):
        try:
            resp = requests.get(
                url,
                headers=headers,
                auth=auth,
                verify=verify_ssl,
                timeout=timeout,
            )
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            content = e.response.text if e.response else "No response content"
            raise RuntimeError(
                f"pfSense API HTTP error {e.response.status_code}: {content}"
            ) from e
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Timeout calling {url}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"Network error calling pfSense API: {str(e)}"
            ) from e

        try:
            return resp.json()
        except ValueError as e:
            raise RuntimeError(
                f"Invalid JSON from pfSense API at {url}"
            ) from e

    def _get_arp_clients(self, api_base, headers, auth, verify_ssl):
        url = f"{api_base}/api/v2/diagnostics/arp_table?limit=0&offset=0"
        data = self._call_api(url, headers, auth, verify_ssl)

        arp_table = data.get("data")
        if not isinstance(arp_table, list):
            raise RuntimeError("Unexpected ARP response structure from pfSense API.")

        total_clients = len(arp_table)
        iface_counts = Counter(
            entry.get("interface", "unknown") for entry in arp_table
        )

        return total_clients, iface_counts

    def _get_system_status(self, api_base, headers, auth, verify_ssl):
        url = f"{api_base}/api/v2/status/system"
        data = self._call_api(url, headers, auth, verify_ssl)

        sys_data = data.get("data", {}) if isinstance(data, dict) else {}

        uptime_raw = sys_data.get("uptime", "N/A")
        uptime_str = uptime_raw

        if isinstance(uptime_raw, str) and uptime_raw != "N/A":
            tokens = uptime_raw.split()
            days = None
            for i, tok in enumerate(tokens):
                if tok.lower().startswith("day"):
                    if i > 0:
                        try:
                            days = int(tokens[i - 1])
                        except ValueError:
                            days = None
                    break
            if days is not None:
                uptime_str = f"{days} days"

        cpu_raw = sys_data.get("cpu_usage")
        mem_raw = sys_data.get("mem_usage")

        cpu = f"{cpu_raw}%" if isinstance(cpu_raw, (int, float)) else "N/A"
        mem = f"{mem_raw}%" if isinstance(mem_raw, (int, float)) else "N/A"

        temp_c = sys_data.get("temp_c")
        temp_f = sys_data.get("temp_f")

        if isinstance(temp_c, (int, float)):
            temp = f"{int(round(temp_c))}°C"
        elif isinstance(temp_f, (int, float)):
            temp = f"{int(round(temp_f))}°F"
        else:
            temp = "N/A"

        return uptime_str, cpu, mem, temp

    def _get_interface_status(self, api_base, headers, auth, verify_ssl):
        url = f"{api_base}/api/v2/status/interfaces"
        data = self._call_api(url, headers, auth, verify_ssl)

        if isinstance(data, dict) and isinstance(data.get("data"), list):
            interfaces = data["data"]
        elif isinstance(data, list):
            interfaces = data
        else:
            interfaces = []

        wan = None
        for iface in interfaces:
            if iface.get("name") == "wan":
                wan = iface
                break

        if not wan and interfaces:
            wan = interfaces[0]

        if not wan:
            return "UNKNOWN", "N/A"

        wan_status = (wan.get("status") or "unknown").upper()
        wan_ip = wan.get("ipaddr") or wan.get("ip") or "N/A"

        return wan_status, wan_ip

    def generate_image(self, settings, device_config):
        title = settings.get("title", "pfSense Status").strip() or "pfSense Status"

        def as_bool(name, default=True):
            val = settings.get(name)
            if val is None:
                return default
            if isinstance(val, str):
                return val.lower() in ("1", "true", "on", "yes")
            return bool(val)

        show_clients = as_bool("show_clients", True)
        show_uptime = as_bool("show_uptime", True)
        show_cpu = as_bool("show_cpu", True)
        show_memory = as_bool("show_memory", True)
        show_temp = as_bool("show_temp", True)
        show_interfaces = as_bool("show_interfaces", True)

        api_base, headers, auth, verify_ssl = self._get_common_config(device_config)

        total_clients, iface_counts = self._get_arp_clients(
            api_base, headers, auth, verify_ssl
        )
        uptime_str, cpu_str, mem_str, temp_str = self._get_system_status(
            api_base, headers, auth, verify_ssl
        )
        wan_status, wan_ip = self._get_interface_status(
            api_base, headers, auth, verify_ssl
        )

        sorted_items = sorted(
            iface_counts.items(),
            key=lambda kv: (0 if kv[0] == "LAN" else 1, kv[0]),
        )

        iface_items = []
        for name, count in sorted_items:
            if total_clients > 0:
                pct = int((count / total_clients) * 100)
            else:
                pct = 0
            iface_items.append({"name": name, "count": count, "pct": pct})

        try:
            width, height = device_config.get_resolution()
        except Exception as e:
            raise RuntimeError(f"Failed to get display resolution: {e}")

        return self.render_image(
            dimensions=(width, height),
            html_file="pfsensestatus.html",
            css_file="pfsensestatus.css",
            template_params={
                "title": title,
                "total_clients": total_clients,
                "uptime": uptime_str,
                "cpu": cpu_str,
                "memory": mem_str,
                "temperature": temp_str,
                "wan_status": wan_status,
                "wan_ip": wan_ip,
                "iface_items": iface_items,
                "show_clients": show_clients,
                "show_uptime": show_uptime,
                "show_cpu": show_cpu,
                "show_memory": show_memory,
                "show_temp": show_temp,
                "show_interfaces": show_interfaces,
                "plugin_settings": settings,
            },
        )

    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        if "title" not in template_params:
            template_params["title"] = "pfSense Status"

        template_params["show_clients"] = True
        template_params["show_uptime"] = True
        template_params["show_cpu"] = True
        template_params["show_memory"] = True
        template_params["show_temp"] = True
        template_params["show_interfaces"] = True
        template_params["style_settings"] = True
        return template_params
