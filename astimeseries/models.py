#!/usr/bin/env python
#
# File: $Id$
#
"""
Modes for the astimeseries django app
"""

# system imports
#

# Django imports
#
from django.db import models
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

# 3rd party improts
#

########################################################################
########################################################################
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
    MIN    = 'min'
    MAX    = 'max'
    FIRST  = 'first'
    LAST   = 'last'
    AVG    = 'avg'

    SUPPORTED_AGG_FUNCTIONS = (MIN, MAX, FIRST, LAST, AVG)

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

    class Meta:
        ordering = ('name',)

    ####################################################################
    #
    def history(self, frm = None, to = None, num_buckets = None,
                bucket_size = 300, aggr_fn = AVG):
        """
        Get and aggregate the values in the time series between (and including)
        'frm' to 'to'. Group them either by the number of buckets asked for or
        the size of the buckets asked for. May not be both. Aggregate them
        according to the specific agggregation function.

        NOTE: You can ask for more than one aggregation function! Basically as
              an optimization. Some queries want to chart the min, max, first,
              last, and average together. That would normally be five
              iterations through the database and although the data is
              hot.. why make those five trips if you know you want all five
              datums when you make the first call.

              If aggr_fn is an interable then each will be applied and the
              result of each returned.

        The values will be cast to the 'fmt' (format) of the time series.

        The result will be of the format:

           [(<time stamp>, <value>), .... ]

        If `aggr_fn` is just one of the aggregation functions the scalar value
        will be returned. If `aggr_fn` is a sequence type, than a list of the
        resulting scalar values will be returned.

        If a caching store (redis) is configured the results of the aggregation
        will be stored there and successive retrievals will get the values from
        there.

        Arguments:
        - `frm`:         consider all samples including this date forward.
                         Defaults to 'None' which is the same as the earliest
                         sample in the time series.
        - `to`:          consider all samples up to and including this date.
                         Defaults to 'None' which is the same as the most
                         recent sample in the time series
        - `num_buckets`: How many buckets to split all of the selected samples
                         between. NOTE: You can specify either num_buckets
                         or bucket_size, but not both
        - `bucket_size`: The size of the buckets. This is in seconds. Defaults
                         to 5 minutes
        - `aggr_fn`:     The type of function for aggregation of raw values in
                         to buckets. A string of 'min', 'max', 'first', 'last',
                         'avg.' Defaults to 'avg'

                         NOTE: This can be a sequence type which contains all of
                               the aggregation functions to use.
        """

        # When producing the result use this boolean to keep track of whether
        # we are returning a scalar result or a list.
        #
        scalar_result = False

        # Turn 'aggr_fn' into a tuple if it is not already an iterable.
        if not hasattr(aggr_fn, "__iter__"):
            scalar_result = True
            aggr_fn = (aggr_fn,)

        for afn in aggr_fn:
            if afn not in SUPPORTED_AGG_FUNCTIONS:
                raise ArgumentError(_("'%s' not a valid aggregation "
                                      "function") % aggr_fn)



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
    def count(self, frm = None, to = None):
        """
        A shortcut to return the number of data in this timeseries.

        Arguments:
        - `frm`:  Count samples after (and including) this date. If 'None'
                  then start from the first sample in this timeseries.
        - `when`: Count samples up to (and including) this date. If 'None'
                  then stop at the last sample in this timeseries
        """
        if frm is None and to is None:
            return self.data.count()
        elif frm is None:
            return self.data.filter(time__gte = frm).count()
        elif to is None:
            return self.data.filter(time__lte = to).count()
        else:
            return self.data.filter(time__gte = frm,time__lte = to).count()

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
