import commons as c
import os
import xml.etree.ElementTree as ET
import re

def get_obligatory_params_names():
    return ['NEXUS', 'REPO', 'GID', 'AID']

def get_obligatory_params():
    return dict(map(lambda x: (x[0], c.gid_to_uri(x[1])) if x[0] == 'GID' else
                    (x[0], x[1]),
                    zip(get_obligatory_params_names(),
                        map(lambda x: c.getenv_or_none(x),
                            get_obligatory_params_names()))))

def check_obligatory_params():
    l = get_obligatory_params()
    ll = map(lambda x: x[0],
             filter(lambda x: x[1] is None,
                    l.items()))
    if len(ll):
        return c.print_and_exit(c.write_log('Not set: %s' % ','.join(ll),
                                            'e'),
                                1)
    return l


def format_base_nexus_url(params):
    return '%s/service/local/repositories/%s/content/%s/%s' % \
        tuple(map(lambda x:params[x],
                                 get_obligatory_params_names()))

def format_snapshot_nexus_url(snapshot):
    return '%s/%s/' % (format_base_nexus_url(check_obligatory_params()),
                       snapshot)

def get_behavior():
    v = c.getenv_or_false('VERSION')
    if not v:
        return 'L'
    if v.upper().endswith('SNAPSHOT'):
        return 'S'
    return 'E'

def get_latest_available_snapshot():
    return sorted(map(lambda x: x.text,
                      filter(lambda x: x.text.endswith('-SNAPSHOT'),
                             ET.fromstring(c.get_url(
                      format_base_nexus_url(check_obligatory_params()) +
                      '/maven-metadata.xml')).findall('versioning/versions/*'))))[-1]

# mcv is most common version
def reduce_to_mcv():
    def exact_to_snapshot():
        return re.split(r'(\d+.\d+.\d+-\d+.\d+-\d+)',
                        c.getenv_or_exit('VERSION'))[0] + '-SNAPSHOT'
    def do_reduce():
        b = get_behavior()
        if b == 'L':
            return get_latest_available_snapshot()
        if b == 'S':
            return c.getenv_or_exit('VERSION')
        if b == 'E':
            return exact_to_snapshot()
    return do_reduce()


def check_version(version):
    def do_check():
        return version in map(lambda x: x.text,
                               ET.fromstring(c.get_url(
                                   format_base_nexus_url(check_obligatory_params()) +
                                   '/maven-metadata.xml')).findall('versioning/versions/*'))
    if not do_check():
       return print_and_exit(write_log('No such version in this repo',
                                       'e'),
                             3)
    return version


def get_artifacts():
    arts = map(lambda x: x.text,
               ET.fromstring(c.get_url(
                   format_snapshot_nexus_url(
                       check_version(
                           reduce_to_mcv())))).findall('data/*/text'))

    lv = sorted(
            filter(lambda x: x is not None,
               list(set(map(
                      lambda x: c.get_or_none(re.split(r'(\d+.\d+.\d+-\d+.\d+-\d+)',
                                         x),
                                1),
                      arts)))),
        key=lambda x: x.split('-')[-1])
    if get_behavior() == 'E':
        iv = getenv_or_exit('VERSION')
        return filter(lambda x: iv in x, arts) if iv in lv else \
            print_and_exit(write_log('No such version',
                                     'e'),
                           3)
    else:
        return filter(lambda x: lv[-1] in x, arts)


def artifact_name_breakdown(name):
    ls = re.split(r'(\d+.\d+.\d+-\d+.\d+-\d+)', name)
    return dict(zip(['a', 'v', 'c', 'e'],
                    [c.getenv_or_exit('AID'),
                     c.get_or_none(ls, 1),
                     c.get_or_none(ls[2].split('.'), 0)[1:],
                     '.'.join(ls[2].split('.')[1:])]))


def prepare_components():
    return map(lambda x: artifact_name_breakdown(x),
               get_artifacts())


def filter_component(art, cn, cv):
    if cv == False:
        return True
    else:
        if art[cn] == cv:
            return True
        else:
            return False


def filter_extensions(art_list):
    return filter(lambda x: filter_component(x,
                                             'e',
                                             c.getenv_or_false('EXT')),
                         art_list)

def filter_classifiers(art_list):
    return filter(lambda x: filter_component(x,
                                             'c',
                                             c.getenv_or_false('CL')),
                         art_list)

def filter_all_components(art_list):
    return filter_classifiers(filter_extensions(art_list))


def format_link(art):
    def no_cls():
        return '%s/service/local/artifact/maven/redirect?r=%s&g=%s&a=%s&v=%s&e=%s' % \
            (c.getenv_or_exit('NEXUS'),
             c.getenv_or_exit('REPO'),
             c.getenv_or_exit('GID'),
             art['a'],
             art['v'],
             art['e'])
    return no_cls() if art['c'] == '' else no_cls() + '&c=%s' % art['c']


def prepare_string(art_list):
    return '\n'.join([format_link(x) for x in art_list])


def run():
    return prepare_string(filter_all_components(prepare_components()))
