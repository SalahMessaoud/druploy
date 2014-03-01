<?php
/**
 * Automatically generated. Do not modify, will be wiped
 */

$aliases['{{ server_alias }}.{{ deployment }}'] = array(
    {% if remote_host is defined %}
    'remote-user' => '{{ remote_user }}',
    'remote-host' => '{{ remote_host }}',
    {% endif %}
    'root' => '{{ root }}',
    'uri' => '{{ site }}',
    'path-aliases' => array(
        '%files' => 'sites/default/files'
    ),
);

