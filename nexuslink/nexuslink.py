import commons as c
import os
import xml.etree.ElementTree as ET
import re


# List of parameters
def get_obligatory_params_names():
    return ['NEXUS', 'REPO', 'GID', 'AID']


# Get all the params from environment
# If parameters is not set, None is placed
# GID is being converted to path, e.g. ab.cd.eg -> ab/cd/eg
def get_obligatory_params():
    return dict(map(lambda x: (x[0], c.gid_to_uri(x[1])) if x[0] == 'GID' else
                    (x[0], x[1]),
                    zip(get_obligatory_params_names(),
                        map(lambda x: c.getenv_or_none(x),
                            get_obligatory_params_names()))))


# Check that parameters are not None
# If not set, will quit with listing of non-set params
# Otherwise, returns map of params
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


# list of obligatory params (see get_obligatory_params) -> nexus api url
# api url: http://NEXUS/service/local/repositories/REPO/content/GID/AID
def format_base_nexus_url(params):
    return '%s/service/local/repositories/%s/content/%s/%s' % \
        tuple(map(lambda x:params[x],
                  get_obligatory_params_names()))


# api url + some version, e.g. snapshot or exact
# add it to format_base_nexus_url()
def format_version_nexus_url(version):
    return '%s/%s/' % (format_base_nexus_url(check_obligatory_params()),
                       version)


# behaviour selector
# based on VERSION param
# if version not passed, L (latest) is returned
# if version endswith 'SNAPSHOT, S (latest for snapshot) is returned
# if version is exact (like 2.1.0 or 1.2.3-TMSTP-BUILD), E (exact) is returned
def get_behavior():
    v = c.getenv_or_false('VERSION')
    if not v:
        return 'L'
    if v.upper().endswith('SNAPSHOT'):
        return 'S'
    return 'E'


# checks if RELEASE environment opt is passed
def is_release():
    return c.getenv_or_false('RELEASE')


# checks maven-metadata.xml and gets the latest version basing on name
# which ends with -SNAPSHOT
def get_latest_available_snapshot():
    return sorted(map(lambda x: x.text,
                      filter(lambda x: x.text.endswith('-SNAPSHOT'),
                             ET.fromstring(c.get_url(
                      format_base_nexus_url(check_obligatory_params()) +
                      '/maven-metadata.xml')).findall('versioning/versions/*'))))[-1]


# check maven-metada.xmk and gets the latest version basing on name
def get_latest_release():
    return sorted(map(lambda x: x.text,
                      ET.fromstring(c.get_url(
                      format_base_nexus_url(check_obligatory_params()) +
                      '/maven-metadata.xml')).findall('versioning/versions/*')))[-1]


# mcv is most common version
# basing on behaviour returns latest snapshot
# that is reqired as metadata can contain not all the possible artifacts
# hence, we go to X.Y.Z-SNAPSHOT and look for exact/latest version there
# if X.Y.Z-SNAPSHOT is stated as VERSION, it is being returned unchanged
# if X.Y.Z-TMSTP-BUILD is stated as VERSION, it is being converted to
#   X.Y.Z-SNAPSHOT
# otherwise nexus api is queried for latest available snapshot
def reduce_to_mcv():
    def exact_to_snapshot(v):
        return re.split(r'(\d+.\d+.\d+-\d+.\d+-\d+)',
                        c.getenv_or_exit('VERSION'))[0] + '-SNAPSHOT'
    def do_reduce():
        b = get_behavior()
        v = c.getenv_or_none('VERSION')
        if b == 'L':
            return get_latest_available_snapshot()
        if b == 'S':
            return v
        if b == 'E':
            return exact_to_snapshot(v)
    return do_reduce()


# if X.Y.Z is stated as VERSION, it is being returned unchanged
# if VERSION is not passed, latest release is returned (see
#   get_latest_release()
# if version is X.Y.Z-TMSP-BUILD, it is converted to X.Y.Z with a warning
def reduce_to_release():
    b = get_behavior()
    v = c.getenv_or_none('VERSION')
    if b == 'L':
        return get_latest_release()
    if b == 'S':
        return c.print_and_call(c.write_log('Assuming release', 'w'),
                                 lambda: v.split('-SNAPSHOT')[0])
    return v


# choose reduce algo basing on RELEASE passed or not
def reduce_to_mcv_2():
    return reduce_to_release() if is_release() else reduce_to_mcv()


# looks for version passed and returns if it exists in nexus, otherwise
# exits with error
def check_version(version):
    def do_check():
        return version in map(lambda x: x.text,
                               ET.fromstring(c.get_url(
                                   format_base_nexus_url(check_obligatory_params()) +
                                   '/maven-metadata.xml')).findall('versioning/versions/*'))
    if not do_check():
       return c.print_and_exit(c.write_log('No such version in this repo',
                                         'e'),
                               3)
    return version


# basing on RELEASE variable chooses regex to match release or snaphsot
# version
def version_splitter():
    return r'(\d+.\d+.\d+)' if is_release() else r'(\d+.\d+.\d+-\d+.\d+-\d+)'


# basing on MCV algo, gets all the artifacts
def get_artifacts():
    arts = map(lambda x: x.text,
               ET.fromstring(c.get_url(
                   format_version_nexus_url(
                       check_version(
                           reduce_to_mcv_2())))).findall('data/*/text'))

    lv = sorted(
            filter(lambda x: x is not None,
               list(set(map(
                      lambda x: c.get_or_none(re.split(version_splitter(), x),
                                1),
                      arts)))),
        key=lambda x: x.split('-')[-1])
    if get_behavior() == 'E':
        iv = c.getenv_or_exit('VERSION')
        return filter(lambda x: iv in x, arts) if iv in lv else \
            c.print_and_exit(c.write_log('No such version',
                                     'e'),
                           3)
    else:
        return filter(lambda x: lv[-1] in x, arts)


# breaks artifacts-X.Y.Z(-TMSTP-BUILD)(-classifier).extension to GAVE[C]
def artifact_name_breakdown(name):
    ls = re.split(version_splitter(), name)
    return dict(zip(['a', 'v', 'c', 'e'],
                    [c.getenv_or_exit('AID'),
                     c.get_or_none(ls, 1),
                     c.get_or_none(ls[2].split('.'), 0)[1:],
                     '.'.join(ls[2].split('.')[1:])]))


# gets artifats from nexus and breaks names into GAVE[C]
def prepare_components():
    return map(lambda x: artifact_name_breakdown(x),
               get_artifacts())


# comon filtering function for GAVE[C] dict
# accepts GAVE[C], key and value
# if value is False, returns True as we don't need to filter it
# otherwise checks GAVE[C] dict key cn equality to cv
def filter_component(art, cn, cv):
    if cv == False:
        return True
    else:
        if art[cn] == cv:
            return True
        else:
            return False


# filters basing on EXT
def filter_extensions(art_list):
    return filter(lambda x: filter_component(x,
                                             'e',
                                             c.getenv_or_false('EXT')),
                         art_list)


# filters basing on classifier
def filter_classifiers(art_list):
    return filter(lambda x: filter_component(x,
                                             'c',
                                             c.getenv_or_false('CL')),
                         art_list)


# filters all the artifcats, first basing on EXT, then by CL
def filter_all_components(art_list):
    return filter_classifiers(filter_extensions(art_list))


# main function, creates GAV links
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


# runs formatting on all the artifacts found
def prepare_string(art_list):
    return '\n'.join([format_link(x) for x in art_list])

# entrypoint
def run():
    return prepare_string(filter_all_components(prepare_components()))
