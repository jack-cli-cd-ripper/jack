### jack_plugin_lame: user-editable lame plugin for jack

plugin_helpers = {
    'plugin_lame': {
        'type': "encoder",
        'target': "mp3",
        'inverse-quality': 1,
        'cmd': "lame --preset cbr %r --strictly-enforce-ISO %i %o",
        'vbr-cmd': "lame -V %q --vbr-new --nohist --strictly-enforce-ISO %i %o",
        'otf-cmd': "lame --preset cbr %r --strictly-enforce-ISO - %o",
        'vbr-otf-cmd': "lame -V %q --vbr-new --nohist --strictly-enforce-ISO - %o",
        'status_blocksize': 160,
        'bitrate_factor': 1,
        'status_start': "%",
        'percent_fkt': r"""
s = string.split(i['buf'], '\r')
if len(s) >= 2: s=s[-2]
if len(s) == 1: s=s[0]
if string.find(s, "%") >= 0:       # status reporting starts here
    y = string.split(s, "/")
    y1 = string.split(y[1], "(")[0]
    percent = float(y[0]) / float(y1) * 100.0
elif string.find(s, "Frame:") >= 0:    # older versions, like 3.13
    y = string.split(s, "/")
    y0 = string.split(y[0], "[")[-1]
    y1 = string.split(y[1], "]")[0]
    percent = float(y0) / float(y1) * 100.0
else:
    percent = 0
""",
    },
}
