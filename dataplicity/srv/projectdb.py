from __future__ import unicode_literals
from __future__ import print_function

import os
import json
import uuid
from threading import Lock


class ProjectEntry(object):
    """Store a path to a project, and meta information"""
    def __init__(self, project_id=None):
        if project_id is None:
            project_id = uuid.uuid1()
        self.project_id = project_id
        self.device_class = None
        self.path = None
        self.version = 0
        self.data = {}
        self.changed = False

    def __repr__(self):
        return "<project '{}' v{}>".format(self.device_class, self.version)

    @classmethod
    def load(cls, fp):
        """Load an entry from a file like object"""
        entry_data = json.load(fp)
        entry = cls(entry_data['project_id'])
        entry.path = entry.get('path', None)
        entry.device_class = entry.get('device_class', None)
        entry.version = entry.get('version', None)
        entry.date = entry.get('data', None)
        return entry

    def dump(self, fp):
        """Dump JSON to a file object"""
        entry_data = self._serialize()
        json.dump(entry_data, fp)

    def _serialize(self):
        """Convert to serializable form"""
        entry = {
            "project_id": self.project_id,
            "device_class": self.device_class,
            "path": self.path,
            "version": self.version,
            "data": self.data
        }
        return entry


class ProjectDB(object):
    """Manages dataplicity projects"""

    def __init__(self, path):
        self._db_path = path
        self._lock = Lock()
        self._create()

    def _create(self):
        try:
            os.makedirs(self._db_path)
        except:
            return
        else:
            try:
                with open(self.get_path('readme.txt')) as f:
                    f.write("Please do not modify these files")
            except IOError:
                pass

    def _get_path(self, path):
        """Get a path relative to the db root"""
        abs_path = os.path.join(self._db_path, path)
        return abs_path

    def _get_project_path(self, project_id):
        project_path = self.get_path('{}.project'.format(project_id))
        return project_path

    def _read_project_data(self, project_id):
        project_path = self._get_project_path(project_id)
        try:
            with open(project_path, 'rb') as f:
                project_data = json.load(f)
        except IOError:
            project_data = None
        return project_data

    def list(self):
        entries = []
        with self._lock:
            paths = []
            for filename in os.listdir(self._db_path):
                if filename.endswith('.project'):
                    project_path = self._get_path(filename)
                    paths.append(project_path)
            for path in paths:
                entry = ProjectEntry(path)
            entries.append(entry)
        return iter(entries)

    __iter__ = list

    def write(self, entry):
        """Write a single entry"""
        with self._lock:
            project_path = self.get_project_path(entry.project_id)
            with open(project_path, 'wb') as f:
                entry.dump(f)

    def read(self, project_id):
        """Read an entry"""
        with self._lock:
            project_path = self.get_project_path(project_id)
            try:
                with open(project_path, 'rb') as f:
                    entry = ProjectEntry.load(f)
            except:
                entry = None
            return entry

    def get_or_create(self, project_id):
        """Get a project if it exists, otherwise create it"""
        with self._lock:
            project_path = self.get_project_path(project_id)
            try:
                with open(project_path, 'rb') as f:
                    entry = ProjectEntry.load(f)
            except:
                entry = ProjectEntry(project_id)
            return entry
