<?php

$databases['default']['default'] = array(
    'driver' => 'mysql',
    'database' => '{{ name }}',
    'username' => '{{ username }}',
    'password' => '{{ password }}',
    'host' => '{{ host }}',
    'prefix' => '',
);

include_once('./includes/cache.inc');
include_once('./sites/all/modules/contrib/memcache/memcache.inc');
$conf['cache_default_class'] = 'MemCacheDrupal';

