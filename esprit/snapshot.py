from esprit.raw import elasticsearch_url

from datetime import datetime, timedelta
import requests


class BadSnapshotMetaException(Exception):
    pass


class TodaySnapshotMissingException(Exception):
    pass


class FailedSnapshotException(Exception):
    pass


class SnapshotDeleteException(Exception):
    pass


class ESSnapshot(object):
    def __init__(self, snapshot_json):
        self.data = snapshot_json
        self.name = snapshot_json['snapshot']
        self.state = snapshot_json['state']
        self.datetime = datetime.utcfromtimestamp(snapshot_json['start_time_in_millis'] / 1000)

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class ESSnapshotsClient(object):

    def __init__(self, connection, snapshot_repository):
        self.snapshots = []
        # Replace the existing connection's index with the snapshot one
        connection.index = '_snapshot'
        self.snapshots_url = elasticsearch_url(connection, type=snapshot_repository)

    def list_snapshots(self):
        # If we don't have the snapshots, ask ES for them
        if not self.snapshots:
            resp = requests.get(self.snapshots_url + '/_all', timeout=600)

            if 'snapshots' in resp.json():
                try:
                    snap_objs = [ESSnapshot(s) for s in resp.json()['snapshots']]
                except Exception as e:
                    raise BadSnapshotMetaException("Error creating snapshot object: " + e.message + ";")
                self.snapshots = sorted(snap_objs, key=lambda x: x.datetime)

        return self.snapshots

    def check_today_snapshot(self):
        snapshots = self.list_snapshots()
        if snapshots[-1].datetime.date() != datetime.utcnow().date():
            raise TodaySnapshotMissingException('Snapshot appears to be missing for {}'.format(datetime.utcnow().date()))
        elif snapshots[-1].state != 'SUCCESS':
            raise FailedSnapshotException('Snapshot for {} has failed'.format(datetime.utcnow().date()))

    def delete_snapshot(self, snapshot):
        resp = requests.delete(self.snapshots_url + '/' + snapshot.name, timeout=300)
        return resp.status_code == 200

    def prune_snapshots(self, ttl_days, delete_callback=None):
        snapshots = self.list_snapshots()
        results = []
        for snapshot in snapshots:
            if snapshot.datetime < datetime.utcnow() - timedelta(days=ttl_days):
                results.append(self.delete_snapshot(snapshot))
                if delete_callback:
                    delete_callback(snapshot.name)

        # Our snapshots list is outdated, invalidate it
        self.snapshots = []

        if not all(results):
            raise SnapshotDeleteException('Not all snapshots were deleted successfully.')
