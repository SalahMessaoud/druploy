<?php

preg_match('@(.+)\.aliases\.drushrc\.php@i', basename(__FILE__), $matches);
$project_name = $matches[1];

$aliases = array();
$dir_handle = new DirectoryIterator(dirname(__FILE__));
while ($dir_handle->valid()) {
  if ($dir_handle->isDir() && !$dir_handle->isDot()) {
    $alias_handle = new DirectoryIterator($dir_handle->getPathname());  
    while ($alias_handle->valid()) {
      if (!$alias_handle->isDir() && !$dir_handle->isDot()) {
        if (preg_match('@one\.[^\.]+\.aliases\.drushrc\.php@i', $alias_handle->getFilename(), $matches)) {
          include($alias_handle->getPathname());
        }
      }
      $alias_handle->next();
    } 
  } 
  $dir_handle->next();
}

