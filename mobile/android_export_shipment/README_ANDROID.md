# Export Shipment Mobile 1.0.0

Android client for the Four Star Industries Export Shipment Management web app.

Architecture follows the stable QCMS First-App approach:
- one hardened Android WebView
- web app owns all menus, pages and permissions
- cookies + DOM storage preserved for login/session
- no native route injection or duplicate navigation layer
- HTTPS only
- upload/file chooser and authenticated downloads supported
- app URL is entered once at first launch and can be changed from the top-right menu

Package (debug): `com.fourstar.exportshipment.test`
User agent token: `ExportShipmentClassicShell/1.0.0`
