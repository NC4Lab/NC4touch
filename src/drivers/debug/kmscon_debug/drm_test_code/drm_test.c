#include <stdio.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <drm/drm.h> // Corrected include path
#include <unistd.h>  // Added for close()
#include <errno.h>
#include <string.h>

#define DRM_CARD_PATH "/dev/dri/card0"

int main()
{
    int fd;
    struct drm_version version;

    // Open DRM device
    fd = open(DRM_CARD_PATH, O_RDWR | O_CLOEXEC);
    if (fd < 0)
    {
        perror("Failed to open DRM device");
        return 1;
    }

    printf("Opened DRM device: %s\n", DRM_CARD_PATH);

    // Clear the version structure
    memset(&version, 0, sizeof(version));

    // Allocate larger buffers for version strings
    char name[256] = {0}; // Increased size and initialized to zero
    char desc[1024] = {0};
    char date[256] = {0};

    version.name = name;
    version.name_len = sizeof(name) - 1; // Reserve space for null-termination
    version.desc = desc;
    version.desc_len = sizeof(desc) - 1;
    version.date = date;
    version.date_len = sizeof(date) - 1;

    // Query DRM version
    if (ioctl(fd, DRM_IOCTL_VERSION, &version) < 0)
    {
        perror("Failed to get DRM version");
        close(fd);
        return 1;
    }

    // Ensure null-termination for safety
    name[version.name_len] = '\0';
    desc[version.desc_len] = '\0';
    date[version.date_len] = '\0';

    printf("DRM Version: %d.%d.%d\n", version.version_major, version.version_minor, version.version_patchlevel);
    printf("Driver Name: %s\n", version.name);
    printf("Description: %s\n", version.desc);
    printf("Date: %s\n", version.date);

    // Close the DRM device
    close(fd);
    printf("Closed DRM device.\n");

    return 0;
}
