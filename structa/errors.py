# structa: an application for analyzing repetitive data structures
#
# Copyright (c) 2021 Dave Jones <dave@waveform.org.uk>
#
# SPDX-License-Identifier: GPL-2.0-or-later

class ValidationWarning(Warning):
    """
    Warning raised when a value fails to validate against the computed pattern
    or schema.
    """
