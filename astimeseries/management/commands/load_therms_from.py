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
import os.path
import traceback

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
        file_name = os.path.basename(args[0])
        tz = pytz.timezone('US/Pacific')

        # Create our time series if it does not already exist.  If it does
        # exist, empty it out (because for the most part we are loading
        # and re-loading the same data.)
        #
        try:
            t = TimeSeries.objects.get(name=file_name)
            t.data.all().delete()
        except TimeSeries.DoesNotExist, e:
            t = TimeSeries(name=file_name)
            t.save()

        temps = []
        prev_time = None

        for idx, line in enumerate(open(args[0], 'r')):
            line = line.strip()

            # Every 100 lines spit out a '.'
            if idx % 1000 == 0:
                self.stdout.write('.', ending = '')
                self.stdout.flush()

            vals = line.split(' ')
            if len(vals) != 6:
                self.stderr.write("Line %d, bad data: '%s'" % (idx,line))
                next

            try:
                when = datetime.datetime(int(vals[0]), int(vals[1]), int(vals[2]),
                                         int(vals[3]), int(vals[4]), tzinfo=tz)
            except ValueError, e:
                self.stderr.write("One of our values can not be converted: %s" % repr(vals))
                continue

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
            if prev_time != when:
                try:
                    t.insert(sum(temps) / len(temps), prev_time)
                except ZeroDivisionError,e:
                    self.stderr.write("Unable to create datum. time: %s, temps: %s" % (prev_time, temps))
                    raise e
                temps = [float(vals[5])]
                prev_time = when
            else:
                temps.append(float(vals[5]))

        # and at the end, if our array of temps is not empty then insert it
        # because it is our last set of values at the end of the file.
        if len(temps) != 0:
            t.insert(sum(temps) / len(temps), when)
        return









