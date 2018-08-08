#!/usr/bin/env python3

# source ./activate_test_env.sh
# subprojects/libinsane-gobject/examples/test_hw.py <directory>

import os
import sys

import PIL.Image

import gi
gi.require_version('Libinsane', '0.1')
from gi.repository import GObject  # noqa: E402
from gi.repository import Libinsane  # noqa: E402


class Logger(GObject.GObject, Libinsane.Logger):
    def do_log(self, lvl, msg):
        if lvl < Libinsane.LogLevel.WARNING:
            return
        print("{}: {}".format(lvl.value_nick, msg))


def get_devices(api):
    print("Looking for scan devices ...")
    devs = api.list_devices(Libinsane.DeviceLocations.ANY)
    print("Found {} devices".format(len(devs)))
    for dev in devs:
        print("[{}] : [{}]".format(dev.get_dev_id(), dev.to_string()))
    for dev in devs:
        print("")
        dev_id = dev.get_dev_id()
        print("Will use device {}".format(dev_id))
        dev = api.get_device(dev_id)
        print("Using device {}".format(dev.get_name()))
        yield dev


def get_source(dev, source_name):
    print("Looking for scan sources ...")
    sources = dev.get_children()
    print("Found {} scan sources:".format(len(sources)))
    for src in sources:
        print("- {}".format(src.get_name()))
        if src.get_name().lower() == source_name.lower():
            source = src
            break
    else:
        raise Exception("Source '{}' not found".format(source_name))
    print("Will use scan source {}".format(source.get_name()))
    return source


def list_opts(item):
    opts = item.get_options()
    print("Options:")
    for opt in opts:
        try:
            print("- {}={} ({})".format(
                opt.get_name(), opt.get_value(), opt.get_constraint()
            ))
        except Exception as exc:
            print("Failed to read option {}: {}".format(
                opt.get_name(), str(exc)
            ))


def set_opt(item, opt_name, opt_value):
    print("Setting {} to {}".format(opt_name, opt_value))
    opts = item.get_options()
    opts = {opt.get_name(): opt for opt in opts}
    if opt_name not in opts:
        print("Option '{}' not found".format(opt_name))
        return
    print("- Old {}: {}".format(opt_name, opts[opt_name].get_value()))
    print("- Allowed values: {}".format(opts[opt_name].get_constraint()))
    opts[opt_name].set_value(opt_value)
    opts = item.get_options()
    opts = {opt.get_name(): opt for opt in opts}
    print("- New {}: {}".format(opt_name, opts[opt_name].get_value()))


def raw_to_img(params, img_bytes):
    fmt = params.get_format()
    if fmt == Libinsane.ImgFormat.RAW_RGB_24:
        (w, h) = (
            params.get_width(),
            int(len(img_bytes) / 3 / params.get_width())
        )
        mode = "RGB"
    elif fmt == Libinsane.ImgFormat.GRAYSCALE_8:
        (w, h) = (
            params.get_width(),
            int(len(img_bytes) / params.get_width())
        )
        mode = "L"
    elif fmt == Libinsane.ImgFormat.BW_1:
        assert()  # TODO
    else:
        assert()  # unexpected format
    print("Mode: {} : Size: {}x{}".format(mode, w, h))
    return PIL.Image.frombuffer(mode, (w, h), img_bytes, "raw", mode, 0, 1)


def scan(source, output_file):
    session = source.scan_start()

    scan_params = source.get_scan_parameters()
    print("Expected scan parameters: {} ; {}x{} = {} bytes".format(
          scan_params.get_format(),
          scan_params.get_width(), scan_params.get_height(),
          scan_params.get_image_size()))

    try:
        page_nb = 0

        assert(not session.end_of_feed())

        img = []
        print("Scanning page --> {} ...".format(output_file))
        while not session.end_of_page():
            data = session.read_bytes(32 * 1024)
            data = data.get_data()
            img.append(data)
        img = b"".join(img)
        img = raw_to_img(scan_params, img)
        print("Saving page as {} ...".format(output_file))
        img.save(output_file)
        print("Page scanned".format(page_nb))

        assert(session.end_of_page())
        # TODO(Jflesch): HP ScanJet 4300C
        # assert(session.end_of_feed())
    finally:
        session.cancel()


def main():
    Libinsane.register_logger(Logger())

    if len(sys.argv) <= 1 or (sys.argv[1] == "-h" or sys.argv[1] == "--help"):
        print("Syntax: {} <output directory>".format(sys.argv[0]))
        sys.exit(1)

    output_dir = sys.argv[1]

    print("Will write the scan result into {}/".format(output_dir))
    os.mkdir(output_dir)

    api = Libinsane.Api.new_safebet()

    print("Looking for devices ...")

    for dev in get_devices(api):
        output_file = os.path.join(output_dir, dev.get_name() + ".jpeg")

        print("Looking for source flatbed ...")
        src = get_source(dev, "flatbed")
        list_opts(src)

        # set the options
        set_opt(src, 'resolution', 150)

        print("Scanning ...")
        scan(src, output_file)
        print("Scan done")

    print("All scan done")


if __name__ == "__main__":
    main()
