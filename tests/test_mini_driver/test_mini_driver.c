// SPDX-License-Identifier: GPL-2.0+
/*
 * test_mini_driver.c
 * A minimal "Hello World" SPI driver for demonstration.
 */
#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/of.h>

/* Match table for of_platform binding */
static const struct of_device_id test_mini_of_match[] = {
    {.compatible = "mytest,mini"},
    {/* sentinel */}};
MODULE_DEVICE_TABLE(of, test_mini_of_match);

static int test_mini_probe(struct spi_device *spi)
{
    dev_info(&spi->dev, "test_mini_driver: Probed! (dev=%s)\n", dev_name(&spi->dev));
    return 0; /* success */
}

static int test_mini_remove(struct spi_device *spi)
{
    dev_info(&spi->dev, "test_mini_driver: Removed! (dev=%s)\n", dev_name(&spi->dev));
    return 0;
}

/* SPI driver struct */
static struct spi_driver test_mini_spi_driver = {
    .driver = {
        .name = "test_mini",
        .owner = THIS_MODULE,
        .of_match_table = test_mini_of_match,
    },
    .probe = test_mini_probe,
    .remove = test_mini_remove,
};

module_spi_driver(test_mini_spi_driver);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("YourNameHere");
MODULE_DESCRIPTION("Minimal SPI driver to test overlay loading");
