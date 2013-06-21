This is an app for django for storing and manipulating timeseries.

It is not intended for heavy industrial use because of the simplistic
way we store the raw values in the database.

It is expected to be fairly performant when fetching new data for
timeseries that have been previously fetched.

It accomplishes this (when this part is written) performance by using
a caching system and a well understood set of what data has changed
between data fetches that can be typified via the arguments used
(basically a kind of memoization of the fetches that deal with the
most common case of new data being added to the end of the
timeseries.)

It supports a number of simple mathematical operations that run on
timeseries as well and the results of these operations are also cached
to give decent performance.

Operations like bucketing are a given as well as addition,
subtraction, running averages, derivatives over time, etc.

