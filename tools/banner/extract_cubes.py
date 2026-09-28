"""Pull cube centres and sizes out of voxel_object.blend (meshes "Left — voxels", "Right — voxels").

blender -b voxel_object.blend --python extract_cubes.py  -> blender-cubes.json
"""
import bpy, bmesh, json
out = {}
for name in ('Left — voxels', 'Right — voxels'):
    o = bpy.data.objects[name]; bm = bmesh.new(); bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table(); seen = set(); cubes = []
    for v in bm.verts:
        if v.index in seen: continue
        stack = [v]; isl = []
        seen.add(v.index)
        while stack:
            a = stack.pop(); isl.append(a.co.copy())
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen: seen.add(b.index); stack.append(b)
        xs = [c.x for c in isl]; ys = [c.y for c in isl]; zs = [c.z for c in isl]
        cubes.append([(min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2, max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)])
    out[name.split()[0].lower()] = cubes
    print(name, len(cubes), 'verts/cube', len(bm.verts)/len(cubes), 'size', [round(v,3) for v in cubes[0][3:]])
json.dump(out, open('blender-cubes.json', 'w'))
