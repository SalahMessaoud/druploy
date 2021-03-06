druploy
=======

# Introduction #

Druploy is an agile deployment tool based on Fabric and Drush that makes deploying instances of Drupal projects fast and easy.
It depends on the Chef [Drupal Cookbook](https://github.com/willieseabrook/drupal-cookbook)

There are some other Drupal deployment tools available (e.g Aegir is an amazing tool) but they are quite heavy and don't work 
as I would like with a number of standard scenarios.

Druploy intends to ease some very standard, day to day problems in the workflow of a Drupal agency

1. Enable the quick onboarding of a new developer into an existing project (by being able to type a single command to have a working copy of a project set up on his machine)
2. Make it easy to show a customer a development/developer branch on a publicly accessable new staging vhost
3. Make it easy for developers to move code/files/databases between development and staging machines
4. Be able to deploy a new site based on a branch and database/file snapshots in a single command
5. Make feature branching a single command (druploy branch command will create a new local git branch, database, files and update settings files)

# Requirements #

1. [Python 2.7.x](http://www.python.org/)
2. [Fabric](http://docs.fabfile.org/en/1.8/)
3. A server could be configured manually with Git, Drush, PHP, Apache, MySQl etc. But the best shortcut to configure your
server is to use the accompanying chef Drupal recipe [Drupal Cookbook](https://github.com/willieseabrook/drupal-cookbook)

# Installation #

1. Install Python, Fabric, Chef
2. cp examples/servers.yaml servers.yaml
2.1 Configure the correct usernames and passwords

    sudo ln -s /path/to/checkout/bin/druploy /usr/bin/druploy

# Usage #

The following example will collect code, database and files from a project not managed by Druploy, and deploy them 
to the domain www.mydrupalsite.com on the server named "live" in your servers.yaml

    druploy server:local source:/path/to/drupal/sites/default code:git@git.domain.com:repo.git,branch=test database:updating=True files:updating=True server:live project:new deploy:live domain:www.mydrupalsite.com

