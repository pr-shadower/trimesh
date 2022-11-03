try:
    from . import generic as g
except BaseException:
    import generic as g

from trimesh.scene.transforms import EnforcedForest


def random_chr():
    return chr(ord('a') + int(round(g.np.random.random() * 25)))


class GraphTests(g.unittest.TestCase):

    def test_forest(self):
        graph = EnforcedForest()
        for i in range(5000):
            graph.add_edge(random_chr(), random_chr())

    def test_cache(self):
        for i in range(10):
            scene = g.trimesh.Scene()
            scene.add_geometry(g.trimesh.creation.box())

            mod = [scene.graph.__hash__()]
            scene.set_camera()
            mod.append(scene.graph.__hash__())
            assert mod[-1] != mod[-2]

            assert not g.np.allclose(
                scene.camera_transform,
                g.np.eye(4))
            scene.camera_transform = g.np.eye(4)
            mod.append(scene.graph.__hash__())
            assert mod[-1] != mod[-2]

            assert g.np.allclose(
                scene.camera_transform,
                g.np.eye(4))
            assert mod[-1] != mod[-2]

    def test_successors(self):
        s = g.get_mesh('CesiumMilkTruck.glb')
        assert len(s.graph.nodes_geometry) == 5

        # world should be root frame
        assert (s.graph.transforms.successors(
            s.graph.base_frame) == set(s.graph.nodes))

        for n in s.graph.nodes:
            # successors should always return subset of nodes
            succ = s.graph.transforms.successors(n)
            assert succ.issubset(
                s.graph.nodes)
            # we self-include node in successors
            assert n in succ

        # test getting a subscene from successors
        ss = s.subscene('3')
        assert len(ss.geometry) == 1
        assert len(ss.graph.nodes_geometry) == 1

        assert isinstance(s.graph.to_networkx(),
                          g.nx.DiGraph)

    def test_nodes(self):
        # get a scene graph
        graph = g.get_mesh('cycloidal.3DXML').graph
        # get any non-root node
        node = next(iter((set(graph.nodes).difference(
            [graph.base_frame]))))
        # remove that node
        graph.transforms.remove_node(node)
        # should have dumped the cache and removed the node
        assert node not in graph.nodes

    def test_kwargs(self):
        # test the function that converts various
        # arguments into a homogeneous transformation
        f = g.trimesh.scene.transforms.kwargs_to_matrix
        # no arguments should be an identity matrix
        assert g.np.allclose(f(), g.np.eye(4))

        # a passed matrix should return immediately
        fix = g.np.random.random((4, 4))
        assert g.np.allclose(f(matrix=fix), fix)

        quat = g.trimesh.unitize([1, 2, 3, 1])
        trans = [1.0, 2.0, 3.0]
        rot = g.trimesh.transformations.quaternion_matrix(quat)
        # should be the same as passed to transformations
        assert g.np.allclose(rot, f(quaternion=quat))

        # try passing both quaternion and translation
        combine = f(quaternion=quat, translation=trans)
        # should be the same as passed and computed
        assert g.np.allclose(combine[:3, :3], rot[:3, :3])
        assert g.np.allclose(combine[:3, 3], trans)

    def test_remove_node(self):
        s = g.get_mesh("CesiumMilkTruck.glb")

        assert len(s.graph.nodes_geometry) == 5
        assert len(s.graph.nodes) == 9
        assert len(s.graph.transforms.node_data) == 9
        assert len(s.graph.transforms.edge_data) == 8
        assert len(s.graph.transforms.parents) == 8

        assert s.graph.transforms.remove_node("1")

        assert len(s.graph.nodes_geometry) == 5
        assert len(s.graph.nodes) == 8
        assert len(s.graph.transforms.node_data) == 8
        assert len(s.graph.transforms.edge_data) == 6
        assert len(s.graph.transforms.parents) == 6

    def test_subscene(self):
        s = g.get_mesh("CesiumMilkTruck.glb")

        assert len(s.graph.nodes) == 9
        assert len(s.graph.transforms.node_data) == 9
        assert len(s.graph.transforms.edge_data) == 8

        ss = s.subscene('3')

        assert ss.graph.base_frame == '3'
        assert set(ss.graph.nodes) == {'3', '4'}
        assert len(ss.graph.transforms.node_data) == 2
        assert len(ss.graph.transforms.edge_data) == 1
        assert list(ss.graph.transforms.edge_data.keys()) == [('3', '4')]

    def test_scene_transform(self):
        # get a scene graph
        scene = g.get_mesh('cycloidal.3DXML')

        # copy the original bounds of the scene's convex hull
        b = scene.convex_hull.bounds.tolist()
        # dump it into a single mesh
        m = scene.dump(concatenate=True)

        # mesh bounds should match exactly
        assert g.np.allclose(m.bounds, b)
        assert g.np.allclose(scene.convex_hull.bounds, b)

        # get a random rotation matrix
        T = g.trimesh.transformations.random_rotation_matrix()

        # apply it to both the mesh and the scene
        m.apply_transform(T)
        scene.apply_transform(T)

        # the mesh and scene should have the same bounds
        assert g.np.allclose(m.convex_hull.bounds,
                             scene.convex_hull.bounds)
        # should have moved from original position
        assert not g.np.allclose(m.convex_hull.bounds, b)

    def test_reverse(self):
        tf = g.trimesh.transformations

        s = g.trimesh.scene.Scene()
        s.add_geometry(
            g.trimesh.creation.box(),
            parent_node_name='world',
            node_name='foo',
            transform=tf.translation_matrix([0, 0, 1]))

        s.add_geometry(
            g.trimesh.creation.box(),
            parent_node_name='foo',
            node_name='foo2',
            transform=tf.translation_matrix([0, 0, 1]))

        assert len(s.graph.transforms.edge_data) == 2
        a = s.graph.get('world', 'foo2')

        assert len(s.graph.transforms.edge_data) == 2

        b = s.graph.get('foo2')
        # get should not have edited edge data
        assert len(s.graph.transforms.edge_data) == 2

        # matrix should be the same both ways
        assert g.np.allclose(b[0], a[0])


if __name__ == '__main__':
    g.trimesh.util.attach_to_log()
    g.unittest.main()
