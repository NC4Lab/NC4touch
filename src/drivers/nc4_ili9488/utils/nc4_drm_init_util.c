#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <sys/mman.h>
#include <drm/drm.h>
#include <drm/drm_mode.h>
#include <xf86drm.h>
#include <xf86drmMode.h>
#include <syslog.h>

// Debugging macro for consistent logging
#define DRM_DEBUG_KMS(fmt, ...) syslog(LOG_INFO, "nc4_ili9488: [nc4_drm_init_util] " fmt, ##__VA_ARGS__)

/***************************************************************************
 * nc4_drm_init_util.c
 *
 * Utility to initialize DRM pipelines for three display panels.
 *
 * This program:
 * - Dynamically iterates over DRM devices (/dev/dri/cardX).
 * - Fetches DRM resources and identifies connected displays.
 * - Creates a dumb framebuffer and sets a mode for each display.
 * - Fills the framebuffer with a solid color (white) for testing.
 *
 * Designed for use with the nc4_ili9488 project on SPI1 with three displays.
 *
 * Limitations:
 * - Assumes fixed configuration of three displays on SPI1.
 * - No timeout or retry logic for unavailable resources.
 *
 * Author: <Your Name>
 ******************************************************************************/

int initialize_display(int card_num)
{
    char device_path[20];
    snprintf(device_path, sizeof(device_path), "/dev/dri/card%d", card_num);

    /***************************************************************************
     * Open DRM Device
     *
     * Opens the DRM device file (e.g., /dev/dri/cardX) to access display hardware.
     * - Ensures read/write access to the DRM subsystem.
     * - Exits with an error if the device is unavailable.
     **************************************************************************/
    int drm_fd = open(device_path, O_RDWR | 0);
    if (drm_fd < 0)
    {
        DRM_DEBUG_KMS("Failed to open DRM device %s: %s\n", device_path, strerror(errno));
        return 1;
    }
    DRM_DEBUG_KMS("Opened DRM device %s successfully\n", device_path);

    /***************************************************************************
     * Fetch DRM Resources
     **************************************************************************/
    drmModeRes *resources = drmModeGetResources(drm_fd);
    if (!resources)
    {
        DRM_DEBUG_KMS("Failed to get DRM resources for %s: %s\n", device_path, strerror(errno));
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Fetched DRM resources for %s successfully\n", device_path);

    /***************************************************************************
     * Find Connected Display Connector
     **************************************************************************/
    drmModeConnector *connector = NULL;
    drmModeModeInfo mode;
    int connector_id = -1;

    for (int i = 0; i < resources->count_connectors; i++)
    {
        connector = drmModeGetConnector(drm_fd, resources->connectors[i]);
        if (connector && connector->connection == DRM_MODE_CONNECTED && connector->count_modes > 0)
        {
            mode = connector->modes[0]; // Use the first mode (e.g., 320x480)
            connector_id = connector->connector_id;
            DRM_DEBUG_KMS("Connector %d is connected with mode %ux%u\n", connector_id, mode.hdisplay, mode.vdisplay);
            break;
        }
        drmModeFreeConnector(connector);
    }

    if (connector_id < 0)
    {
        DRM_DEBUG_KMS("No connected connector found for %s\n", device_path);
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }

    /***************************************************************************
     * Create Dumb Buffer
     **************************************************************************/
    struct drm_mode_create_dumb create = {0};

    create.width = mode.hdisplay;  // Set buffer width to match display resolution.
    create.height = mode.vdisplay; // Set buffer height to match display resolution.
    create.bpp = 32;               // Bits per pixel (supports 24-bit color with alpha).

    if (drmIoctl(drm_fd, DRM_IOCTL_MODE_CREATE_DUMB, &create) < 0)
    {
        DRM_DEBUG_KMS("Failed to create dumb buffer for %s: %s\n", device_path, strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Dumb buffer created: handle=%u, pitch=%u, size=%llu\n", create.handle, create.pitch, create.size);

    /***************************************************************************
     * Add Framebuffer
     **************************************************************************/
    uint32_t fb_id;
    if (drmModeAddFB(drm_fd, create.width, create.height, 24, 32, create.pitch, create.handle, &fb_id))
    {
        DRM_DEBUG_KMS("Failed to add framebuffer for %s: %s\n", device_path, strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Framebuffer added with ID=%u for %s\n", fb_id, device_path);

    /***************************************************************************
     * Map Dumb Buffer
     **************************************************************************/
    struct drm_mode_map_dumb map = {0};
    map.handle = create.handle;

    if (drmIoctl(drm_fd, DRM_IOCTL_MODE_MAP_DUMB, &map) < 0)
    {
        DRM_DEBUG_KMS("Failed to map dumb buffer for %s: %s\n", device_path, strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }
    DRM_DEBUG_KMS("Dumb buffer mapped at offset=%llu\n", map.offset);

    void *fb = mmap(0, create.size, PROT_READ | PROT_WRITE, MAP_SHARED, drm_fd, map.offset);
    if (fb == MAP_FAILED)
    {
        DRM_DEBUG_KMS("Failed to mmap framebuffer for %s: %s\n", device_path, strerror(errno));
        drmModeFreeResources(resources);
        close(drm_fd);
        return 1;
    }

    // Fill the buffer with a solid color (white)
    memset(fb, 0xFF, create.size);
    DRM_DEBUG_KMS("Framebuffer filled with white color for %s\n", device_path);

    /***************************************************************************
     * Set Display Mode
     **************************************************************************/
    int crtc_id = resources->crtcs[0];
    if (drmModeSetCrtc(drm_fd, crtc_id, fb_id, 0, 0, &connector_id, 1, &mode))
    {
        DRM_DEBUG_KMS("Failed to set CRTC for %s: %s\n", device_path, strerror(errno));
    }
    else
    {
        DRM_DEBUG_KMS("CRTC set successfully for %s with mode %ux%u on connector %d\n", device_path, mode.hdisplay, mode.vdisplay, connector_id);
    }

    drmModeFreeResources(resources);
    close(drm_fd);
    return 0;
}

int main()
{
    for (int card_num = 0; card_num < 3; card_num++)
    {
        DRM_DEBUG_KMS("Initializing display for card%d\n", card_num);
        if (initialize_display(card_num) != 0)
        {
            DRM_DEBUG_KMS("Failed to initialize card%d\n", card_num);
        }
    }
    return 0;
}
