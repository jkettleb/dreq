
# coding: utf-8

# In[1]:

import sys
sys.path.append('.')
import operator
import itertools
import re

import cmip6_gdoc

dreq = cmip6_gdoc.open('./data/CMIP6_datareq_UKESM_mappings_161117_1141_updated.xlsx', filt=False)
dold = cmip6_gdoc.open('./data/CMIP6_datareq_UKESM_mappings.xlsx', filt=False)

# In[3]:

def not_deleted(rec):
    result = True
    if rec.last_update:
        result = 'DELETE' not in rec.last_update
    return result

def produce(rec):
    result = True
    if rec.plan:
        result = rec.plan.strip() not in ('do-not-produce', 'request-error') 
    return result

doll = filter(not_deleted, dold)
dnew = filter(not_deleted, dreq)

def mip_id(a):
    return str(a.mip_id)

def clean_cell_methods(a):
    return re.sub('\(comment:.*\)', '(comment:..)', str(a))

def _clean_dims(dim):
    d = re.sub('time\d+', 'time', dim)
    return sorted(d.split())

def _clean_freq(freq):
    return re.sub('Pt', '', freq)

def is_move(a, b):
    same_cell = clean_cell_methods(a.cell_methods) == clean_cell_methods(b.cell_methods)
    same_dims = _clean_dims(a.dimension) == _clean_dims(b.dimension)
    same_name = a.cf_std_name == b.cf_std_name or a.title == b.title
    same_freq = _clean_freq(a.frequency) == _clean_freq(b.frequency)
    return all((same_cell, same_dims, same_name, same_freq))

def find_moves(adds, dels):
    moves = []
    for a in adds:
        for d in dels:
            if is_move(a, d):
                moves.append((a, d))
    return moves

def _from_moves(moves, ind):
    return [move[ind] for move in moves]

def identify_moves(adds, dels):
    moves = find_moves(adds, dels)

    real_adds = filter(lambda x: x not in _from_moves(moves, 0), adds)
    real_dels = filter(lambda x: x not in _from_moves(moves, 1), dels)

    return moves, real_adds, real_dels

def same(a): return a

def clean_cell_methods(a): return re.sub('\(comment:.*\)', '(comment:..)', str(a))

def clean_units(a):
    try:
        result = float(str(a))
    except ValueError:
        result = str(a)
    return result

def clean_positive(a):
    result = a
    if str(a) in ('None', 'none'):
        result = None
    return result

CMPS= {'cell_methods':clean_cell_methods, 'dimension':same, 'units':clean_units,
      'positive':clean_positive}
       
def cmp_records(r1, r2):
    """Returns dictionary comparing elements of namedtuple."""
    result = dict()
    for field, func in CMPS.iteritems():
        val1 = getattr(r1, field)
        val2 = getattr(r2, field)
        if func(val1) != func(val2):
            result[field] = (func(val1), func(val2))
    return result

def records_diffs(v1, v2):
    """Returns dictionary summarising differences between xcel versions."""
    def _as_set_dict(vals):
        adict = {entry.mip_id: entry for entry in vals}
        ids = set(adict.keys())
        return ids, adict
    
    ids1, d1 = _as_set_dict(v1)
    ids2, d2 = _as_set_dict(v2)
   
    updates = []
    for mipid in ids1 & ids2:
        diffs = cmp_records(d1[mipid], d2[mipid])
        if diffs:
            updates.append((d2[mipid], d1[mipid]))

    added = [d2[key] for key in (ids2 - ids1)]
    removed = [d1[key] for key in (ids1 - ids2)]

    moves, radd, rrem = identify_moves(added, removed)
    return {'added': radd,
            'removed': rrem,
            'moved': moves,
            'updated': updates}

diffs = records_diffs(doll, dnew)

def first_mip(a):
    return a[0].mip_id

cmor = operator.attrgetter('cmor_label')

pp = operator.attrgetter('cmor_label', 'miptable', 'cf_std_name', 'title', 'plan', 'ukesm_component', 'requesting_mips')
def pretty(a, sep='$', display=pp):
    return sep.join(map(str, display(a)))

print 'updated'
def component(move):
    return move[1].ukesm_component

updates = sorted(filter(lambda x: produce(x[1]), diffs['updated']), key=component)
for component, update_group in itertools.groupby(updates, component):
    print '---', component
    for update in update_group:
        print pretty(update[1], ', ', display=operator.attrgetter('mip_id', 'title', 'plan')), cmp_records(update[0], update[1])

exit() # temporary

print 'removed'
with open('data/rm_at_17.csv', 'w') as fi:
    fi.write('$'.join(('cmor_label', 'miptable', 'cf_std_name', 'title', 'plan', 'ukesm_component', 'requesting_mips')) + '\n')
    for rem in sorted(filter(produce, diffs['removed']), key = cmor):
        fi.write(pretty(rem) + '\n')

print 'added'
for add in sorted(diffs['added'], key = mip_id):
    print pretty(add)

print 'moved'
for move in sorted(diffs['moved'], key=first_mip):
    print mip_id(move[0]), pretty(move[1], ', ', display=operator.attrgetter('mip_id', 'plan'))


exit()
# Looking at differences based on Matt's analysis
# -----------------------------------------------

# In[12]:


def deleted(rec):
    return rec.last_update and '01.00.17:DELETE' in rec.last_update
def added(rec):
    return rec.last_update and '01.00.17:ADD' in rec.last_update
def changed(rec):
    return rec.last_update and '01.00.17' in rec.last_update and not deleted(rec) and not added(rec)

dels = filter(deleted, dreq)
adds = filter(added, dreq)
change = filter(changed, dreq)


# In[11]:


def not_cf3hr(rec):
    return rec.miptable != 'CF3hr'

def produce(rec):
    return rec.plan not in ('do-not-produce', 'request-error')

_info = operator.attrgetter('mip_id', 'cf_std_name', 'cell_methods', 'dimension', 'requesting_mips', 'plan')

print 'moves---'
for move in moves:
    print mip_id(move[1]), mip_id(move[0]), move[1].plan

print 'adds---'
for rec in map(_info, filter(not_cf3hr, real_adds)):
    print ', '.join(map(str, rec))

print 'dels---'
for rec in map(_info, filter(produce, real_dels)):
    print ', '.join(map(str, rec))


# In[18]:

for rec in filter(produce, change):
    print ', '.join(map(str, _info(rec))), rec.last_update

