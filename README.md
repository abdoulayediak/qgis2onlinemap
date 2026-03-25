# Qgis2OnlineMap - QGIS Plugin

**Qgis2OnlineMap** is a companion QGIS plugin that allows you to directly upload, publish, and manage your exported QGIS web maps without dealing with servers, hosting, or complicated configurations. It works as a bridge between your QGIS workspace and the [Qgis2OnlineMap](https://qgis2onlinemap.com) cloud platform.

## Features

- **Direct Publishing**: Upload your exported map folders or .zip files directly from your QGIS interface.
- **Drag & Drop**: Simply drag a folder from your file explorer into the plugin to prepare an upload.
- **Projects Tab**: View and manage all your uploaded maps, check their online status, and copy links instantly.
- **Secure Authentication**: Uses encrypted tokens via a secure browser-based login. You never type your password in QGIS.
- **Auto-Reset Workflow**: The plugin automatically clears the upload form after a successful publish, preventing accidental overwrites.
- **Custom Theming**: Choose between the modern Qgis2OnlineMap interface or a native QGIS look via the **Settings** tab.

## Quick Start Guide

1.  **Authenticate**: 
    - Open the plugin and go to the **Settings** tab.
    - Click **Login via Web Browser**. This will launch your browser and securely pass an authentication key back to the plugin.
    - Verify your status shows a green icon: **🟢 Status: Logged In**.

2.  **Publish a Map**:
    - Go to the **Publish Map** tab.
    - **Drag & Drop** your webmap folder into the dashed area (or use the browse button).
    - The **Map Title** will auto-populate; feel free to override it.
    - Click **Publish**. A progress bar will track the transfer.

3.  **Projects & Actions**:
    - Navigate to the **Projects** tab.
    - **👁️ View**: Opens the live URL in your browser.
    - **🔗 Copy**: Copies the viewer link to your clipboard.
    - **🔄 Update**: Overwrites an existing map's files while keeping the same URL and settings.

## Security & Access

- **Revoking Access**: If you ever need to lock out your desktop plugin, log into the web dashboard, navigate to **Account**, and click **Revoke Access**. 
- **Status Indicator**: If your access is revoked, the plugin will display **⚪ Status: Revoked (Check Web Dashboard)**. You will need to generate a new key on the website to re-authenticate.

## About

**Author:** Abdoulaye Diakite  
**Website:** [qgis2onlinemap.com](https://qgis2onlinemap.com)  
**Demo:** [Sydney CBD (hosted 3D map)](https://qgis2onlinemap.com/v/571ef7c8)

*Built for QGIS users pushing the boundaries of spatial data sharing.*
