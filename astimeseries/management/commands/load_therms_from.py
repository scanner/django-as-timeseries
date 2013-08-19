#!/usr/bin/env python
#
# File: $Id$
#
"""
A django management command for bulk loading old Apricot Systematic therm
data. This is not going to be that useful to others except as example code.
"""

# system imports
#
import datetime

# 3rd party impots
#
import pytz

# django imports
#
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now, utc
from django.utils.encoding import smart_str
from astimeseries.models import TimeSeries, Datum

########################################################################
########################################################################
#
class Command(BaseCommand):
    """
    Read datafile in our therms temperature format and insert the values as
    data in a timeseries.
    """

    args = '<file name>'
    help = "Loads the therms data from the given file in to a timeseries " \
        "with the same name as the file."

    ####################################################################
    #
    def handle(self, *args, **options):
        """
        Read lines from the given file, inserting the therm values in to the
        time series named by the file as data.

        The format of the lines in the file is:

            2013 08 18 16 17 73.94

        '2013.08.18T16:17 73.94 degrees F' in local time.

        NOTE: we do several readings a minute, but we do not store a seconds
              value so we need to average the values for the same minute
              together for a single value.

        Arguments:
        - `*args`: Expect one argument that is the name of the file.
        - `**options`:
        """
        file_name = args[0]
        tz = pytz.timezone('US/Pacific')
        try:
            t = TimeSeries.objecs.get(name=file_name)
        temps = []
        prev_time = None

        for line in open(file_name, 'r'):
            vals = line.split(' ')

            when = datetime.datetime(int(vals[0]), int(vals[1]), int(vals[2]),
                                     int(vals[3]), int(vals[4]), tzinfo=tz)

            # Since we are summing all the temps within a single minute we
            # have to start with the first minute..
            #
            if prev_time == None:
                prev_time = when

            # If the current minute is different than the previous minute then
            # we have read all of the temps within that minute. Create a datum
            # attached to our time series that is the average of the temps we
            # read in this minute.
            #
            if prev_time != when
                t.insert(sum(temps) / len(temps), prev_time)
                temps = []

        # and at the end, if our array of temps is not empty then insert it
        # because it is our last set of values at the end of the file.
        if len(temps) != 0:
            t.insert(sum(temps) / len(temps), when)

        return









