#!/bin/bash
set -euo pipefail
ROOT="${1:-.}"
SRC="$ROOT/mobile/android_export_shipment/app/src/main/java/com/fourstar/exportshipment/MainActivity.java"
GRADLE="$ROOT/mobile/android_export_shipment/app/build.gradle"
MANIFEST="$ROOT/mobile/android_export_shipment/app/src/main/AndroidManifest.xml"
WF="$ROOT/.github/workflows/export-shipment-android-test-apk.yml"
ICON="$ROOT/mobile/android_export_shipment/app/src/main/res/drawable-nodpi/fsi_shipment_icon.png"
for f in "$SRC" "$GRADLE" "$MANIFEST" "$WF" "$ICON"; do [ -f "$f" ] || { echo "Missing: $f"; exit 1; }; done
grep -Fq 'ExportShipmentClassicShell/1.0.0' "$SRC"
grep -Fq 'private WebView webView;' "$SRC"
grep -Fq 'setAcceptThirdPartyCookies' "$SRC"
grep -Fq 'onShowFileChooser' "$SRC"
grep -Fq 'setDownloadListener' "$SRC"
grep -Fq 'return false;' "$SRC"
grep -Fq "applicationId 'com.fourstar.exportshipment'" "$GRADLE"
grep -Fq "versionName '1.0.0'" "$GRADLE"
grep -Fq 'versionCode 1' "$GRADLE"
grep -Fq 'android:usesCleartextTraffic="false"' "$MANIFEST"
grep -Fq 'name: Export Shipment Android First-App APK' "$WF"
grep -Fq 'actions/setup-java@v4' "$WF"
grep -Fq 'gradle-version:' "$WF"
grep -Fq 'Export-Shipment-Mobile-FIRST-APP-APK' "$WF"
if grep -Eq 'appendQueryParameter\("(native_mobile|native_nav|page|route|shipment_route|shipment_native_route)"' "$SRC"; then echo 'Native route injection found'; exit 1; fi
if grep -Eq '(openDrawer|closeDrawer|__shipmentNativeNavigate|toggleStreamlitSidebar)' "$SRC"; then echo 'Native navigation bridge found'; exit 1; fi
# Resource reference sanity
! grep -R -q '@drawable/stawn_icon\|@color/qcms_' "$ROOT/mobile/android_export_shipment/app/src/main/res"
echo 'Export Shipment Android First-App v1.0.0 static verification: PASS'
