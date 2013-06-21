"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import datetime

from django.test import TestCase

from django.utils.timezone import now, utc
from django.utils.encoding import smart_str
from astimeseries.models import TimeSeries, Datum

####################################################################
#
def pt(t):
    """
    Given a posix timestamp (seconds since unix epoch) return a
    datetime, with the timezone set to utc.

    Shortened to make it quick to use in our test module.

    Arguments:
    - `t`: float or integer representing the posix timestamp
    """
    return datetime.datetime.utcfromtimestamp(t).replace(tzinfo = utc)


#
# Construct some test data
#
TS_DATA_01 = [(pt(x),x) for x in range(0,100,5)]

########################################################################
########################################################################
#
class BasicTimeSeries(TestCase):
    """
    test basic functions of our timeseries and datum classes
    """

    ####################################################################
    #
    def setUp(self, ):
        """
        Setup our basic timeseries object
        """
        t = TimeSeries(name="test")
        t.save()
        for x,y in TS_DATA_01:
            t.insert(y,x)
        return

    ####################################################################
    #
    def test_count(self):
        """
        Test the various arguments to the 'count()' time series method
        """
        t = TimeSeries.objects.get(name = "test")
        self.assertEqual(t.count(), 20)
        return

    ####################################################################
    #
    def test_get_raw_series(self):
        """
        Test retrieving all of the raw values for a series and make sure they
        match the data used to create the series
        """
        t = TimeSeries.objects.get(name = "test")
        raw = t.raw_history()
        for idx, elt in enumerate(TS_DATA_01):
            self.assertEqual(elt[0],raw[idx][0])
            self.assertEqual(smart_str(elt[1]), smart_str(raw[idx][1]))
        return

    ####################################################################
    #
    def get_raw_series_with_range(self):
        """
        Test retrieving a range of values from the raw series
        """
        return

    ####################################################################
    #
    def get_collated_min(self):
        """
        Test getting a the values in a series collated by 'min()'
        """
        return

    ####################################################################
    #
    def get_collated_max(self):
        """
        Test getting the values in a series collated by 'max()'
        """
        return

    ####################################################################
    #
    def get_collated_first(self):
        """
        """
        return
