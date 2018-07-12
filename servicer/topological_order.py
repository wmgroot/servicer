from functools import reduce

# destructive topological dependency sort
# expects a dict containing dependency sets
# http://rosettacode.org/wiki/Topological_sort#Python
def toposort2(data):
    result = []

    if not data:
        return result

    for k, v in data.items():
        v.discard(k) # Ignore self dependencies

    # ensure all referenced items have an entry in the data dict
    extra_items_in_dependencies = reduce(set.union, data.values()) - set(data.keys())
    data.update({item: set() for item in extra_items_in_dependencies})

    # perform the topological ordering
    while True:
        ordered = set(item for item, dependency in data.items() if not dependency)
        if not ordered:
            break

        # build the next topological layer
        result.append(sorted(ordered))

        # remove the current layer's dependenices from each item
        data = {item: (dep - ordered) for item, dep in data.items() if item not in ordered}

    assert not data, 'A cyclic dependency exists amongst %r' % data

    return result

if __name__ == '__main__':
    # sample execution
    data = {
        'des_system_lib':   set('std synopsys std_cell_lib des_system_lib dw02 dw01 ramlib ieee'.split()),
        'dw01':             set('ieee dw01 dware gtech'.split()),
        'dw02':             set('ieee dw02 dware'.split()),
        'dw03':             set('std synopsys dware dw03 dw02 dw01 ieee gtech'.split()),
        'dw04':             set('dw04 ieee dw01 dware gtech'.split()),
        'dw05':             set('dw05 ieee dware'.split()),
        'dw06':             set('dw06 ieee dware'.split()),
        'dw07':             set('ieee dware'.split()),
        'dware':            set('ieee dware'.split()),
        'gtech':            set('ieee gtech'.split()),
        'ramlib':           set('std ieee'.split()),
        'std_cell_lib':     set('ieee std_cell_lib'.split()),
        'synopsys':         set(),
    }

    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(data)

    result = toposort2(data)
    print('result:')
    pp.pprint(result)
