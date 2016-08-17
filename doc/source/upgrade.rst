Contrail upgrades (experimental)
================================

Description
-----------

Starting from version 4.0.1 the Fuel Contrail Plugin includes the set of tasks and
scripts that allow the cloud administrator to upgrade the Contrail packages
along with Contrail configuration with minimal downtime to production network.
The upgrade process is divided into tasks, that modify only the components that need
to be upgraded without touching other OpenStack components.
The packages are updated using the plugin-based repository, and configuration files
are updated using the templates included in the latest plugin version.
Controllers and compute nodes are upgraded separately, using puppet manifests
provided with plugin. Other contrail-specific roles such as DPDK-compute, SR-IOV-compute,
and TSN are not supported yet.

Prequisites
-----------

This guide assumes that you have installed Fuel 8.0 with the Fuel Contrail plugin,
and successfully deployed the environment according to :doc:`/install_guide`.

Package versions supported:

* Fuel Contrail plugin  >= 4.0.0
* Juniper Contrail >= 3.0.0

Update the packages on Fuel Master node
---------------------------------------

#. Obtain the latest package of Fuel Contrail plugin that supports your Fuel version.

#. Copy the rpm package downloaded at previous step to the Fuel Master node

   .. code-block:: console

      scp contrail-4.0-4.0.1-1.noarch.rpm <Fuel Master node ip>:/tmp/

#. Log in to the Fuel Master node and upgrade the plugin:

   .. code-block:: console

      ssh <the Fuel Master node ip>
      fuel plugins --update /tmp/contrail-4.0-4.0.1-1.noarch.rpm

#. Copy the latest Juniper Contrail installation package to the Fuel Master node and run the installation
   script to unpack the vendor package and populate the plugin repository with up-to-date packages:

   .. code-block:: console

      scp contrail-install-packages_3.0.2.1-4~liberty_all.deb \
          <Fuel Master node ip>:/var/www/nailgun/plugins/contrail-4.0/
      ssh <Fuel Master node ip> /var/www/nailgun/plugins/contrail-4.0/install.sh

.. raw:: latex

    \clearpage

Upgrade Contrail and OpenStack Controllers
------------------------------------------

The first upgrade step involves the controllers, both for OpenStack and Contrail.
Upgrade tasks stop Contrail config services for the time of upgrade, this will
stop Neutron operations for 10-20 minutes without affecting the workload.
The Contrail control nodes will be upgraded and restarted one-by-one to keep
BGP and XMPP connectivity.
After the tasks have been finished on contrail nodes, the upgrade of OpenStack controllers
starts. The Neutron service will be restarted in case if contrail core plugin will be upgraded.

#. Log in to Fuel Master node, change the working directory to plugin folder:

   .. code-block:: console

      ssh <the Fuel Master node ip>
      cd /var/www/nailgun/plugins/contrail-4.0/

#. Start the upgrade of control plane:

   .. code-block:: console

      ./upgrade.sh controllers

#. Run the contrail service verification steps from :doc:`/verification` to ensure that all
   Contrail services are up and running.
   You can verify the version of Contrail packages using Contrail Web UI or ``contrail-version``
   CLI command.

Upgrade Compute nodes
---------------------

After the control plane has been upgraded, you can upgrade OpenStack Compute nodes.
The upgrade task can install the latest version of Contrail vRouter,
correctly replacing the kernel module without host reboot.
The task upgrades compute hosts one by one, in ascending order by node ID.
The instances running on particular compute node will lose network connectivity
during the vRouter upgrade, this can take up to 5 min.

#. Log in to the Fuel Master node, change the working directory to the plugin's folder:

   .. code-block:: console

      ssh <the Fuel Master node ip>
      cd /var/www/nailgun/plugins/contrail-4.0/

#. Start the upgrade of control plane:

   .. code-block:: console

      ./upgrade.sh computes

#. Log in to compute nodes and verify output of the ``contrail-status`` command.
   You can verify the version of the vRouter package by running ``contrail-version`` command.