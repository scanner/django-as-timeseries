#!/usr/bin/env python
#
# File: $Id$
#
"""
Modes for the astimeseries django app
"""

# system imports
#
import decimal

# Django imports
#
from django.db import models
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

# 3rd party improts
#

# Rounding factors. When doing various historical queries usually the caller is
# going to want the buckets rounded to some nice factor.
#
# So if the user has not specified an exact set of start/end times and bucket
# sizes we are going to fudge their query so that the result begins and ends on
# a nice factor of the range they are asking for.
#
# The bucket size is chosen so that not only is it a nice factor of the range
# being fetched, but that the start and end of the range been queried will be
# on one of the multiples of these minutes.
#
# For minutes:
# 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30
#
# For hours:
# 1, 2, 3, 4, 6, 8, 12
#

# When we are auto-configuring the bucket size based on the range these are the
# time ranges that select a certain bucket size (and a certain start/end time
# rounded value)
#
RANGES = (
    (1800,  10),   # 30 minutes - 10 second buckets
    (3600,  20),   # 60 minutes - 20 second buckets
    (7200,  40),   # 2 hours - 40 second buckets
    (10800, 60),   # 3 hours - 1 minute
    (14400, 120),  # 4 hours - 2 minute buckets
    (21600, 180),  # 6 hours - 3 minute buckets
    (28800, 240),  # 8 hours - 4 minute buckets
    (43200, 300),  # 12 hours - 5 minute buckets
    (57600, 360),  # 18 hours - 6 minute buckets
    (86400, 600),  # 2 days - 10 minute buckets
    (259200, 900), # 3 days - 15 minute
    (345600, 1200), # 4 days - 20 minute
    (604800, 1800), # 7 days - 30 minute
    (1209600, 3600), # 14 days - 1 hour
    (2592000, 7200), # 30 days - 2 hour
    (5184000, 10800), # 60 days - 3 hour
    (10368000, 14400), # 120 days - 4 hour
    (20736000, 36000), # 240 days - 10 hour
    (31536000, 86400), # 1 year - 1 day
    # 1.5 years
    # 2 years
    # 3 years
    # 5 years
    # 10 years
    )

########################################################################
########################################################################
#
# XXX I think we are going to call this 'node' and have 'timeseries' be a new
#     class that represents just bucketed time series and has hash and array
#     like access methods (and stuff so we can tie just the aggregated
#     timeseries to cached structures in redis or whatever.)
#
class TimeSeries(models.Model):
    """
    A timeseries.

    A user can track certain bits of metadata associated with a timeseries in
    this class as well:

    o The type of the data
    o The class - counter, gauge, or undefined

    Type - Although the values are stored as strings (why bother using anything
          else if our accelerator backend - redis - only uses strings
          anyways...) any given timeseries has a preferred type ('fmt' because
          'type' is a reserved word in python) for its values to be interpreted
          as.

          What is more one of the support types is 'decimal' based on the
          python decimal library and if that is selected we need to know the
          resolution to apply.

    Class - in dealing with many kinds of timeseries (especially when dealing
            with SNMP gathered data) we may be dealing with either a 'counter'
            or a 'gauge.' A counter is one where the value grows continuously
            over time. Such as number of TCP sessions initiated. A gauge will
            go up and down according to the value of the variable tracks - such
            as the number of current TCP sessions. Since we may not know or
            care what the value is we also have 'undefined'.


    """

    # Aggregation functions we support
    #
    MIN    = 'min'    # Min of all of the values in the bucket
    MAX    = 'max'    # Max of all of the values in the bucket
    FIRST  = 'first'  # First value that falls in to the bucket
    LAST   = 'last'   # Last value that falls in to the bucket
    MEAN   = 'mean'   # Mean of all of the points taht fall in to the bucket
    STDDEV = 'stddev' # Standard deviation between all the points that
                      # fall in to the bucket.

    # NOTE: Look up normal, triangular, and uniform probability densities
    # see: http://blog.velir.com/index.php/2013/07/11/visualizing-data-uncertainty-an-experiment-with-d3-js/
    #
    SUPPORTED_AGG_FUNCTIONS = (MIN, MAX, FIRST, LAST, MEAN, STDDEV)

    # The types we support that cause the individual values to be coerced into
    # the expected type
    #
    INT     = 'int' # Python integer
    FLOAT   = 'flo' # Python float
    DECIMAL = 'dec' # Python decimal module - it will use the 'precision'
                    # field to set the precision.
    RAW     = 'raw' # This field is returned as is (a string)
    FORMAT_CHOICES = (
        (INT,     "Integer"),
        (FLOAT,   "Float"),
        (DECIMAL, "Decimal"),
        (RAW,     "Raw"),
        )

    FORMAT_CAST_FN = {
        INT    : int,
        FLOAT  : float,
        DECIMAL: decimal.Decimal,
        RAW    : lambda x: x,
        }

    # The possible classes for this time series
    #
    GAUGE     = 'gau' # Gauge - value can vary up and down
    COUNTER   = 'cou' # Counter - value is absolutely increasing over time
    UNDEFINED = 'und' # Undefined - we do not know and probably do not care
    CLASS_CHOICES = (
        (GAUGE,     'Gauge'),
        (COUNTER,   'Counter'),
        (UNDEFINED, 'Undefined'),
        )

    ##########
    ##########
    ###
    ### Data fields
    ###
    name = models.CharField(_('name'), max_length = 1024, db_index = True)
    created = models.DateTimeField(_('created'), auto_now_add = True,
                                   help_text = _('The time at which '
                                                 'this timeseries was '
                                                 'created'))

    # NOTE: For 'updated' we set this even if we are just adding a value to the
    #       time series, yes this is more writes.
    #
    updated = models.DateTimeField(_('updated'), auto_now = True,
                                   help_text = _('The timestamp of the last '
                                                 'update of this timeseries'))
    fmt = models.CharField(_('format'), max_length = 3,
                           choices = FORMAT_CHOICES,
                           default = INT,
                           help_text = _('The format (type) of the values in '
                                         'this timeseries'))
    precision = models.SmallIntegerField(_('precision'), default = 2,
                                         help_text = \
                                             _('If the type of the values in '
                                               'this timeseries is "decimal" '
                                               'this is the precision we will '
                                               'use to represent them'))
    cls = models.CharField(_('class'), max_length = 3,
                           choices = CLASS_CHOICES, default = UNDEFINED,
                           help_text = _('Lets us track if this timeseries is '
                                         'counter or a gauge (or undefined)'))
    ###
    ###
    ##########
    ##########
    ###
    ### django model Meta class
    ###
    class Meta:
        ordering = ('name',)

    ####################################################################
    #
    def nhistory(self, frm, to, num_buckets = None, bucket_size = None,
                 aggr_fn = STDDEV):
        """

        Arguments:
        - `frm`:
        - `to`:
        - `num_buckets`:
        - `bucket_size`:
        - `aggr_fn`:
        """
        if aggr_fn not in SUPPORTED_AGG_FUNCTIONS:
            raise ArgumentError(_("'%s' not a valid aggregation function") % \
                                    aggr_fn)

        # If the 'frm' is None then the 'from' time is the first sample in our
        # time series. Ditto if 'to' is None then the 'to' time is the last
        # sample in our time series.
        #
        # If the num_buckets and bucket_size are both None the caller wants us
        # to determine reasonable numbers for these. This will be based on the
        # size of the range that they have asked for.
        #
        if num_buckets is None and bucket_size is None:
            # If 'frm' or 'to' are None then we need to go to the time series
            # and fill them in with the first and/or last timestamps.
            #
            if to is None:
                to = self.data.all()[0].time
            if frm is None:
                frm = self.data.all().order_by("-time")[0]

            #
        return

    ####################################################################
    #
    def history(self, frm = None, to = None, num_buckets = None,
                bucket_size = None, aggr_fn = STDDEV):
        """
        Get and aggregate the values in the time series between (and including)
        'frm' to 'to'. Group them either by the number of buckets asked for or
        the size of the buckets asked for. May not be both. Aggregate them
        according to the specific agggregation function.

        If neither num_bukcets nor bucket_size is specified the history()
        method will try to decide an appropriate value mainly based on the date
        range specified.

        The values will be cast to the 'fmt' (format) of the time series.

        The result will be of the format:

           [(<time stamp>, <value>), .... ]

        NOTE: If a caching store (redis) is configured the results of the
              aggregation will be stored there and successive retrievals will
              get the values from there.

        NOTE: If a caching store is configured we will actually compute all of
              the possible aggregation functions since computing and storing
              the result in the cache is cheap and will save us if the same
              query is made with a different aggregation function while the
              cache is still valid.

        Arguments:
        - `frm`:         consider all samples including this date forward.
                         Defaults to 'None' which is the same as the earliest
                         sample in the time series.
        - `to`:          consider all samples up to and including this date.
                         Defaults to 'None' which is the same as the most
                         recent sample in the time series
        - `num_buckets`: How many buckets to split all of the selected samples
                         between.

                         NOTE: You can specify either num_buckets or
                               bucket_size, but not both. If neither are
                               specified history() will try to figure out a
                               good value based on the date range.

        - `bucket_size`: The size of the buckets. This is in seconds. Defaults
                         to 5 minutes
        - `aggr_fn`:     The type of function for aggregation of raw values in
                         to buckets. A string of 'min', 'max', 'first', 'last',
                         'stddev.' Defaults to 'stddev'
        """

        # make sure the caller specified a valid aggregation function.
        #
        if aggr_fn not in SUPPORTED_AGG_FUNCTIONS:
            raise ArgumentError(_("'%s' not a valid aggregation function") % \
                                    aggr_fn)

        # If frm & to are both None then that means we need to fetch the entire
        # range of history values for this timeseries. That is easy enough, but
        # if neither num_buckets nor bucket_size are specified than we need to
        # decide on an appropriate bucket size and to do that we need to know
        # the first and last timestamps of our time series.
        #

        # Set up the filter to determine the range of values we are going to
        # retrieve
        #
        # XXX part of what is going to happen here is to look at the date range
        #     and the bucket size and see if we have any cached series that
        #     match the bucket size and dates of cached series (and if they do
        #     only fetch values that are not already computed by the cached
        #     series)
        #
        kwargs = {}
        if frm is not None:
            kwargs["time__gte", frm]
        if to is not None:
            kwargs["time__lte", to]




        return

    ####################################################################
    #
    def raw_history(self, frm = None, to = None):
        """
        Return the raw history values in our timeseries between frm & to.

        The result is an array of tuples. Each tuple will be a (datetime,value)
        pair.

        Arguments:
        - `frm`:         consider all samples including this date forward.
                         Defaults to 'None' which is the same as the earliest
                         sample in the time series.
        - `to`:          consider all samples up to and including this date.
                         Defaults to 'None' which is the same as the most
                         recent sample in the time series
        """
        kwargs = {}
        if frm is not None:
            kwargs["time__gte", frm]
        if to is not None:
            kwargs["time__lte", to]

        # Retrieve the values from the db and return them to the user
        #
        # XXX I guess this is where we would wrap it in a memoized like cache
        #     call
        #
        # XXX I am returning a list which actually fetches all values from the
        #     db. Maybe I should use an generator comprehension instead?
        #
        return [(d.time,d.value) for d in self.data.filter(**kwargs)]

    ####################################################################
    #
    def insert(self, value, when = None):
        """
        Insert the given value to this time series.  You could just
        insert the value directly but this method lets us track
        additions, and if an addition would cause a cached series to
        be no longer be up to date it will delete the cached series so
        the next access to that series will re-compute it.

        There is no return value.

        XXX We did not use 'append' because really you can add values anywhere
            in the time series.. it will almost always be at the end but there
            will be a number of times when it is not..

        Arguments:
        - `value`: The value to add to the time series
        - `when`:  The datetime being added. If not specified we assume 'utcnow'
        """
        if when is None:
            when = now()
        self.data.create(time = when, value = value)
        return

    ####################################################################
    #
    def current(self):
        """
        Return the current value of this timeseries (node)
        """
        return self.cast(self.data.all()[0])

    ####################################################################
    #
    def cast(self, value):
        """
        Convert the string value in to the value type (cls) for this time
        series.

        XXX We need to check if the cls is 'Decimal' and if it is call the cast
            function with the precision context.

        Arguments:
        - `value`:
        """
        return FORMAT_CAST_FN[self.cls](value)

    ####################################################################
    #
    def count(self, frm = None, to = None):
        """
        A shortcut to return the number of data in this timeseries.

        Arguments:
        - `frm`:  Count samples after (and including) this date. If 'None'
                  then start from the first sample in this timeseries.
        - `when`: Count samples up to (and including) this date. If 'None'
                  then stop at the last sample in this timeseries
        """
        kwargs = {}
        if frm is not None:
            kwargs["time__gte", frm]
        if to is not None:
            kwargs["time__lte", to]
        return self.data.filter(**kwargs).count()

    ####################################################################
    #
    def __unicode__(self):
        return u"%s" % self.name

########################################################################
########################################################################
#
class Datum(models.Model):
    """
    A datum attached to a timeseries. It holds a time stamp and a value
    (and of course the timeseries it is attached to.)

    The value is stored as a string. This may seem odd since we are typically
    storing integers and floats and operating on them but we need to be able to
    handle multiple types and having multiple columns in the db, and having to
    add a new column whenever we defined a new type seemed wrong.

    Also our caching accelerators that we plan on using (redis) store values as
    strings anyways..
    """
    timeseries = models.ForeignKey(TimeSeries,
                                   verbose_name = _('time series'),
                                   help_text = _('Time series this datum'
                                                 'belongs to'),
                                   related_name = 'data')
    time = models.DateTimeField(_('time'), db_index = True,
                                help_text = _('The time of this datum'))
    value = models.CharField(_('value'), max_length = 256,
                           help_text = _('The value of this datum'))

    class Meta:
        ordering = ("timeseries","time")

    ####################################################################
    #
    def __unicode__(self):
        return u"%s(%s@'%s')" % (self.timeseries.name, self.value,
                                        self.time)
