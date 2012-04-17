import logging
from google.appengine.api import memcache
from google.appengine.api import app_identity
import common

def auto_cache(expiration=600, key=None):
    """
    A decorator to memoize the results of a function call in memcache. Use this
    in preference to doing your own memcaching, as this function avoids version
    collisions etc...

    Note that if you are not providing a key (or a function to create one) then your
    arguments need to provide consistent str representations of themselves. Without an
    implementation you could get the memory address as part of the result - "<... object at 0x1aeff0>"
    which is going to vary per request and thus defeat the caching.
    
    Usage:
    @auto_cache
    get_by_type(type):
        return MyModel.all().filter("type =", type)
    
    :param expiration: Number of seconds before the value is forced to re-cache, 0
    for indefinite caching
    
    :param key: Option manual key, use in combination with expiration=0 to have
    memcaching with manual updating (eg by cron job). Key can be a func(*args, **kwargs)

    :rtype: Memoized return value of function
    """
    
    def wrapper(fn):
        def cache_decorator(*args, **kwargs):

            dev_bypass = common.IS_SDK or common.IS_REMOTE_DEV
            if dev_bypass and not ENABLE_DEV_AUTO_CACHE:
                return fn(*args, **kwargs)

            mc_key = None
            if key:
                if callable(key):
                    mc_key = key(*args, **kwargs)
                else:
                    mc_key = key
            else:
                mc_key = '%s:%s-%s-%s' % ("auto_cache", fn.func_name, str(args), str(kwargs))
            
            if ENABLE_VERSIONED_AUTO_CACHE:
                mc_key += "-" + common.CURRENT_VERSION_ID            
                                
            result = memcache.get(mc_key)
            
            if not result:
                result = fn(*args, **kwargs)

                try:
                    memcache.set(mc_key, result, time=expiration)
                except ValueError, e:
                    logging.critical("Recevied error from memcache", exc_info=e)

            return result
        return cache_decorator
    return wrapper
