"""Copyright 2016 Mirantis, Inc.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
"""

import os

from proboscis import test

from fuelweb_test.helpers.decorators import log_snapshot_after_test
from fuelweb_test.settings import CONTRAIL_PLUGIN_PACK_UB_PATH
from fuelweb_test.tests.base_test_case import SetupEnvironment
from fuelweb_test.tests.base_test_case import TestBasic

from helpers import plugin
from helpers import openstack
from helpers import baremetal
from tests.test_contrail_check import TestContrailCheck


@test(groups=["contrail_sriov_tests"])
class SRIOVTests(TestBasic):
    """SRIOV Tests."""

    pack_copy_path = '/var/www/nailgun/plugins/contrail-4.0'
    add_package = '/var/www/nailgun/plugins/contrail-4.0/'\
                  'repositories/ubuntu/contrail-setup*'
    ostf_msg = 'OSTF tests passed successfully.'
    cluster_id = ''
    pack_path = CONTRAIL_PLUGIN_PACK_UB_PATH
    CONTRAIL_DISTRIBUTION = os.environ.get('CONTRAIL_DISTRIBUTION')
    bm_drv = baremetal.BMDriver()

    @test(depends_on=[SetupEnvironment.prepare_slaves_9],
          groups=["contrail_ha_sriov"])
    @log_snapshot_after_test
    def contrail_ha_sriov(self):
        """Check Contrail deploy on HA environment.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration and CEPH storage
            2. Enable and configure Contrail plugin
            3. Deploy cluster with following node configuration:
                node-01: 'controller';
                node-02: 'controller';
                node-03: 'controller', 'ceph-osd';
                node-04: 'compute', 'ceph-osd';
                node-05: 'compute', 'ceph-osd';
                node-06: 'contrail-db';
                node-07: 'contrail-config';
                node-08: 'contrail-control';
                node-09: 'contrail-analytics';
                node-sriov: 'compute', sriov';
            4. Run OSTF tests
            5. Run contrail health check tests

        Duration 120 min

        """
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=9,
                                       options={'images_ceph': True,
                                                'volumes_ceph': True,
                                                'ephemeral_ceph': True,
                                                'objects_ceph': True,
                                                'volumes_lvm': False})
        self.bm_drv.host_prepare()

        self.show_step(2)
        # enable plugin and ativate SR-IOV in contrail settings
        plugin.activate_sriov(self)
        # activate vSRX image
        vsrx_setup_result = plugin.activate_vsrx()

        plugin.show_range(self, 3, 4)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'sriov'])

        conf_nodes = {
            'slave-01': ['controller'],
            'slave-02': ['controller'],
            'slave-03': ['controller', 'ceph-osd'],
            'slave-04': ['compute', 'ceph-osd'],
            'slave-05': ['compute', 'ceph-osd'],
            'slave-06': ['contrail-db'],
            'slave-07': ['contrail-config'],
            'slave-08': ['contrail-control'],
            'slave-09': ['contrail-analytics']
        }
        # Cluster configuration
        self.fuel_web.update_nodes(self.cluster_id,
                                   nodes_dict=conf_nodes,
                                   update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        if vsrx_setup_result:
            self.fuel_web.run_ostf(
                cluster_id=self.cluster_id,
                test_sets=['smoke', 'sanity', 'ha'],
                should_fail=1,
                failed_test_name=['Instance live migration'])
            self.show_step(5)
            TestContrailCheck(self).cloud_check(['sriov', 'contrail'])

    @test(depends_on=[SetupEnvironment.prepare_slaves_5],
          groups=["contrail_sriov_add_compute"])
    @log_snapshot_after_test
    def contrail_sriov_add_compute(self):
        """Verify that Contrail compute role can be added after deploying.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Deploy cluster with following node configuration:
                node-1: 'controller', 'ceph-osd';
                node-2: 'contrail-config', 'contrail-control',
                        'contrail-db', 'contrail-analytics';
                node-3: 'contrail-db';
                node-4: 'compute', 'ceph-osd';
                node-5: 'compute', 'ceph-osd';
                node-bm: 'compute', 'sriov';
            4. Run OSTF tests
            5. Add one node with following configuration:
                node-6: "compute", "ceph-osd";
            6. Deploy changes
            7. Run OSTF tests
            8. Run contrail health check tests

        """
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=5,
                                       options={'images_ceph': True,
                                                'volumes_ceph': True,
                                                'ephemeral_ceph': True,
                                                'objects_ceph': True,
                                                'volumes_lvm': False})
        self.bm_drv.host_prepare()

        self.show_step(2)
        # enable plugin and enable SR-IOV in contrail settings
        plugin.activate_sriov(self)
        # activate vSRX image
        vsrx_setup_result = plugin.activate_vsrx()

        self.show_step(3)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'sriov'])
        conf_nodes = {
            'slave-01': ['controller', 'ceph-osd'],
            'slave-02': ['contrail-config',
                         'contrail-control',
                         'contrail-db',
                         'contrail-analytics'],
            'slave-03': ['compute', 'ceph-osd'],
            'slave-04': ['compute', 'ceph-osd'],
        }
        conf_compute = {'slave-06': ['compute', 'ceph-osd']}

        # Cluster configuration
        self.fuel_web.update_nodes(self.cluster_id,
                                   nodes_dict=conf_nodes,
                                   update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        self.show_step(4)
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   should_fail=1,
                                   failed_test_name=['Instance live migration']
                                   )
            TestContrailCheck(self).cloud_check(['sriov', 'contrail'])

        # Add Compute node and check again
        self.show_step(5)
        # Cluster configuration
        self.fuel_web.update_nodes(self.cluster_id,
                                   nodes_dict=conf_compute,
                                   update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        self.show_step(6)
        openstack.deploy_cluster(self)
        # Run OSTF tests
        self.show_step(7)
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   should_fail=1,
                                   failed_test_name=['Instance live migration']
                                   )
            self.show_step(8)
            TestContrailCheck(self).cloud_check(['sriov', 'contrail'])

    @test(depends_on=[SetupEnvironment.prepare_slaves_5],
          groups=["contrail_sriov_delete_compute"])
    @log_snapshot_after_test
    def contrail_sriov_delete_compute(self):
        """Verify that Contrail compute role can be deleted after deploying.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Deploy cluster with following node configuration:
                node-01: 'controller';
                node-02: 'contrail-control', 'contrail-config',
                         'contrail-db', 'contrail-analytics';
                node-03: 'compute', 'cinder';
                node-04: 'compute';
                node-bm: 'compute', 'sriov';
            4. Run OSTF tests
            5. Delete node-04 with "compute" role
            6. Deploy changes
            7. Run OSTF tests
            8. Run contrail health check tests

        """
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=5)
        self.bm_drv.host_prepare()

        self.show_step(2)
        # activate plugin with SRIOV feature
        plugin.activate_sriov(self)
        # activate vSRX image
        vsrx_setup_result = plugin.activate_vsrx()

        self.show_step(3)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'sriov'])
        conf_no_compute = {
            'slave-01': ['controller'],
            'slave-02': ['contrail-control',
                         'contrail-config',
                         'contrail-db',
                         'contrail-analytics'],
            'slave-03': ['compute', 'cinder'],
        }
        conf_compute = {'slave-04': ['compute']}

        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes_dict=dict(conf_no_compute, **conf_compute),
            update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        if vsrx_setup_result:
            self.show_step(4)
            self.fuel_web.run_ostf(cluster_id=self.cluster_id)
            TestContrailCheck(self).cloud_check(['sriov', 'contrail'])

        # Delete Compute node and check again
        self.show_step(5)
        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes_dict=conf_compute,
            pending_addition=False, pending_deletion=True,
            update_interfaces=False)

        # Deploy cluster
        self.show_step(6)
        openstack.deploy_cluster(self)
        # Run OSTF tests
        if vsrx_setup_result:
            self.show_step(7)
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   test_sets=['smoke', 'sanity'],
                                   should_fail=1,
                                   failed_test_name=['Check that required '
                                                     'services are running']
                                   )
            self.show_step(8)
            TestContrailCheck(self).cloud_check(['sriov', 'contrail'])

    @test(depends_on=[SetupEnvironment.prepare_slaves_5],
          groups=["contrail_sriov_add_controller"])
    @log_snapshot_after_test
    def contrail_sriov_add_controller(self):
        """Verify that Contrail controller role can be added after deploying.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Deploy cluster with following node configuration:
                node-1: 'controller', 'ceph-osd';
                node-2: 'contrail-config', 'contrail-control',
                        'contrail-db', 'contrail-analytics';
                node-3: 'compute', 'ceph-osd';
                node-4: 'compute', 'ceph-osd';
                node-bm: 'compute', 'sriov';
            4. Run OSTF tests
            5. Add one node with following configuration:
                node-5: "controller", "ceph-osd";
            6. Deploy changes
            7. Run OSTF tests
            8. Run contrail health check tests

        """
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=5,
                                       options={'images_ceph': True,
                                                'volumes_ceph': True,
                                                'ephemeral_ceph': True,
                                                'objects_ceph': True,
                                                'volumes_lvm': False})
        self.bm_drv.host_prepare()

        self.show_step(2)
        # activate plugin with SRIOV feature
        plugin.activate_sriov(self)
        # activate vSRX image
        vsrx_setup_result = plugin.activate_vsrx()

        self.show_step(3)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'sriov'])
        conf_nodes = {
            'slave-01': ['controller', 'ceph-osd'],
            'slave-02': ['contrail-config',
                         'contrail-control',
                         'contrail-db',
                         'contrail-analytics'],
            'slave-03': ['compute', 'ceph-osd'],
            'slave-04': ['compute', 'ceph-osd'],
        }
        conf_controller = {'slave-05': ['controller', 'ceph-osd']}

        # Cluster configuration
        self.fuel_web.update_nodes(self.cluster_id,
                                   nodes_dict=conf_nodes,
                                   update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        self.show_step(4)
        # FIXME: remove shouldfail, when livemigration+DPDK works
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   should_fail=1,
                                   failed_test_name=['Instance live migration']
                                   )
            TestContrailCheck(self).cloud_check(['sriov', 'contrail'])

        # Add Compute node and check again
        self.show_step(5)
        # Cluster configuration
        self.fuel_web.update_nodes(self.cluster_id,
                                   nodes_dict=conf_controller,
                                   update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        self.show_step(6)
        openstack.deploy_cluster(self)
        # Run OSTF tests
        self.show_step(7)
        # FIXME: remove shouldfail, when livemigration+DPDK works
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   should_fail=1,
                                   failed_test_name=['Instance live migration']
                                   )
            self.show_step(8)
            TestContrailCheck(self).cloud_check(['sriov', 'contrail'])

    @test(depends_on=[SetupEnvironment.prepare_slaves_5],
          groups=["contrail_sriov_delete_controller"])
    @log_snapshot_after_test
    def contrail_sriov_delete_controller(self):
        """Verify that Contrail controller role can be deleted after deploying.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Deploy cluster with following node configuration:
               node-01: 'controller';
               node-02: 'contrail-control', 'contrail-config',
                        'contrail-db', 'contrail-analytics';
               node-03: 'compute', 'cinder';
               node-04: 'controller';
               node-bm: 'compute', 'sriov';
            4. Run OSTF tests
            5. Delete node-04 with "controller" role
            6. Deploy changes
            7. Run OSTF tests
            8. Run contrail health check tests

        """
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=5)
        self.bm_drv.host_prepare()

        self.show_step(2)
        # activate plugin with SRIOV feature
        plugin.activate_sriov(self)
        # activate vSRX image
        vsrx_setup_result = plugin.activate_vsrx()

        plugin.show_range(self, 3, 4)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'sriov'])
        conf_no_compute = {
            'slave-01': ['controller'],
            'slave-02': ['contrail-control',
                         'contrail-config',
                         'contrail-db',
                         'contrail-analytics'],
            'slave-03': ['compute', 'cinder'],
        }
        conf_controller = {'slave-04': ['controller']}

        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes_dict=dict(conf_no_compute, **conf_controller),
            update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id)
            TestContrailCheck(self).cloud_check(['sriov', 'contrail'])

        # Delete Compute node and check again
        plugin.show_range(self, 5, 7)
        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes_dict=conf_controller,
            pending_addition=False, pending_deletion=True,
            update_interfaces=False)

        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   test_sets=['smoke', 'sanity'],
                                   should_fail=1,
                                   failed_test_name=['Check that required '
                                                     'services are running']
                                   )
            self.show_step(8)
            TestContrailCheck(self).cloud_check(['sriov', 'contrail'])

    @test(depends_on=[SetupEnvironment.prepare_slaves_5],
          groups=["contrail_sriov_add_sriov"])
    @log_snapshot_after_test
    def contrail_sriov_add_sriov(self):
        """Verify that SRiOV role can be added after deploying.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Deploy cluster with following node configuration:
                node-01: 'controller', 'ceph-osd';
                node-02: 'contrail-config', 'contrail-control';
                node-03: 'contrail-db', 'contrail-analytics';
                node-04: 'compute', 'ceph-osd';
                node-05: 'compute', 'ceph-osd';
            4. Run OSTF tests
            5. Run contrail health check tests
            6. Add one node with following configuration:
                node-bm: "compute", "sriov";
            7. Deploy changes
            8. Run OSTF tests
            9. Run contrail health check tests

        """
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=5,
                                       options={'images_ceph': True})
        self.bm_drv.host_prepare()

        self.show_step(2)
        # activate plugin with SRiOV feature
        plugin.activate_sriov(self)
        # activate vSRX image
        vsrx_setup_result = plugin.activate_vsrx()

        plugin.show_range(self, 3, 5)
        conf_nodes = {
            'slave-01': ['controller', 'ceph-osd'],
            'slave-02': ['contrail-config', 'contrail-control'],
            'slave-03': ['contrail-db', 'contrail-analytics'],
            'slave-04': ['compute', 'ceph-osd'],
            'slave-05': ['compute', 'ceph-osd'],
        }
        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes_dict=conf_nodes,
            update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id)
            TestContrailCheck(self).cloud_check(['contrail'])

        self.show_step(6)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'sriov'])
        self.show_step(7)
        openstack.deploy_cluster(self)

        self.show_step(8)
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id)
            self.show_step(9)
            TestContrailCheck(self).cloud_check(['sriov', 'contrail'])

    @test(depends_on=[SetupEnvironment.prepare_slaves_9],
          groups=["contrail_sriov_delete_sriov"])
    @log_snapshot_after_test
    def contrail_sriov_delete_sriov(self):
        """Verify that SRiOV role can be deleted after deploying.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Deploy cluster with following node configuration:
                node-01: 'controller';
                node-02: 'controller';
                node-03: 'controller', 'cinder';
                node-04: 'contrail-control', 'contrail-config',
                         'contrail-db', 'contrail-analytics';
                node-05: 'contrail-control', 'contrail-config',
                         'contrail-db', 'contrail-analytics';
                node-06: 'contrail-control', 'contrail-config',
                         'contrail-db', 'contrail-analytics';
                node-07: 'compute';
                node-08: 'compute';
                node-bm: 'compute', 'sriov';
            4. Run OSTF tests
            5. Run contrail health check tests
            6. Delete node-bm with "sriov" and "compute" roles
            7. Deploy changes
            8. Run OSTF tests
            9. Run contrail health check tests

        """
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=9)
        self.bm_drv.host_prepare()

        self.show_step(2)
        # activate plugin with SRiOV feature
        plugin.activate_sriov(self)
        # activate vSRX image
        vsrx_setup_result = plugin.activate_vsrx()

        self.show_step(3)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'sriov'])
        conf_no_dpdk = {
            'slave-01': ['controller'],
            'slave-02': ['controller'],
            'slave-03': ['controller', 'cinder'],
            'slave-04': ['contrail-control',
                         'contrail-config',
                         'contrail-db',
                         'contrail-analytics'],
            'slave-05': ['contrail-control',
                         'contrail-config',
                         'contrail-db',
                         'contrail-analytics'],
            'slave-06': ['contrail-control',
                         'contrail-config',
                         'contrail-db',
                         'contrail-analytics'],
            'slave-07': ['compute'],
            'slave-08': ['compute']
        }

        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes_dict=conf_no_dpdk,
            update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        self.show_step(4)
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id)
            self.show_step(5)
            TestContrailCheck(self).cloud_check(['sriov', 'contrail'])

        self.show_step(6)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'sriov'],
                                    pending_deletion=True,
                                    pending_addition=False)
        self.show_step(7)
        openstack.deploy_cluster(self)

        self.show_step(8)
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   should_fail=1,
                                   failed_test_name=['Check that required '
                                                     'services are running']
                                   )
            self.show_step(9)
            TestContrailCheck(self).cloud_check(['contrail'])