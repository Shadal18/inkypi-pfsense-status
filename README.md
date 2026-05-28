# pfSense Status

An InkyPi plugin that displays key pfSense status information on your e-paper dashboard.

It can show:

- Active clients
- System uptime
- CPU usage
- Memory usage
- Temperature
- Interface summary

## Install

Install the plugin from your InkyPi device:

```bash
inkypi plugin install pfsense_status https://github.com/shadal18/inkypi-pfsense-status
```

## Update

To update the plugin on your InkyPi device:

1. SSH into your InkyPi host.
2. Change into the plugin directory:
   ```bash
   cd ~/InkyPi/src/plugins/pfsense_status
   ```
3. Run this update command:
   ```bash
   git pull origin main && \
   if [ -d pfsense_status ]; then \
     shopt -s dotglob nullglob && \
     mv pfsense_status/* . && \
     rmdir pfsense_status; \
   fi && \
   sudo systemctl restart inkypi.service
   ```

If you do not see changes after updating:

- Confirm you are in the correct plugin folder.
- Clear your browser cache or hard refresh the InkyPi web UI.
- Check the InkyPi logs for any plugin errors.

## pfSense API key setup

This plugin requires a pfSense REST API key, and the key can be created from the pfSense web interface under **System > REST API > Keys** .

To add the key in InkyPi:

1. Open the InkyPi front page.
2. Click the **key icon**.
3. Add a new key named `PFSENSE_API_KEY`.
4. Paste in your pfSense API key.
5. Save it.
6. Restart InkyPi if needed.

## Settings

The plugin settings page lets you customize:

- Title text
- Which cards are displayed
- Optional display sections depending on your layout

## Repository

GitHub repository:

[https://github.com/shadal18/inkypi-pfsense-status](https://github.com/shadal18/inkypi-pfsense-status)
