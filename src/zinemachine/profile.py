from escpos import capabilities


class LMP201(capabilities.Profile):
    """ this is a custom profile for the printer we are using. self-test printout reports its model number as LMP201 """

    def __init__(self):
        # copy profile_data so we don't overwrite Default
        self.profile_data = dict(self.profile_data)

        self.profile_data['name'] = 'LMP201'
        self.profile_data['notes'] = 'Modified from the Default profile to only include supported codepages. Portable BT 80mm Thermal Receipt Printer Mini Bill POS I3F0 (https://www.ebay.com/itm/363749704636?hash=item54b12c03bc:g:rg0AAOSwHP9iIChY&amdata=enc%3AAQAHAAAA8FCrxtaC2HGdZofnlIi9WIqNnFCXLrMXXeZWpD2MRljxLPtaKshA2LqINp2xVimVuyy1szOyRI7Oibi3ckWYkgl%2BY5g6qqaxyopGnkXtiXYNyczEzbRiHQbu2Zc5Dq9Nh8l%2FZtFEq8hlWWq00ZX4FvlKgP0qyj6R887dNAvtHmwD6ASuH%2FevF4OUb1zpHREvyLI2pg239tCEHy4yQIgkJFa7Y6jgQhfJPJ4rJGyvLgHpJ1I8syXTTIRS%2Bbzfe1y4OcLVIm2UM3%2FMkXDU0pVkYRC6VRSIOQZTEDV%2BtAfbZ0nVe%2BeRcG6mxXilhjQftn9RCQ%3D%3D%7Ctkp%3ABk9SR6z59dDfYA)'
        self.profile_data['media']['width']['mm'] = 72
        self.profile_data['media']['width']['pixels'] = 576

        # codepages that the printer has no glyphs for
        self.unsupportedCodepages = ['CP851', 'CP853', 'CP857', 'CP737', 'CP1254', 'CP1255', 'CP1256', 'CP1257', 'CP1258', 'RK1048']

        # codepages that are mapped to non-standard characters, breaking the auto-encoder
        # most of these mismatches are due to the library mapping the name of the codepage to a byte sequence, but the printer actually has a different codepage stored at that address
        # we might be able to fix this by remapping the codepage names. however, many of the codepages are only partially supported by the printer, so we would also need to remap those codepages
        # ISO_8859-15 -> CP720 (incomplete)
        # CP866 -> CP1251
        self.nonstandardCodepages = ['CP866', 'CP775', 'CP720', 'CP861', 'ISO_8859-15', 'CP862', 'CP855', 'CP1125', 'CP869', 'CP1253', 'CP864', 'ISO_8859-7', 'TCVN-3-1', 'TCVN-3-2', 'CP874', 'CP1250', 'CP1251', 'ISO_8859-2', 'CP1251']

        self.profile_data['codePages'] = {i: cp for i, cp in self.profile_data['codePages'].items() if (cp not in self.unsupportedCodepages) and (cp not in self.nonstandardCodepages)}
