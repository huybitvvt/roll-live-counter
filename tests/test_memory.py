import numpy as np
import pytest

from roll_counter.memory import Memory,Store


@pytest.fixture
def memory(tmp_path):
    store = Store(tmp_path/'history.db')
    memory = Memory(store,confirm_frames=2,confirm_seconds=.1)
    yield memory
    store.close()


def item(track,x=0,feature=None):
    return {'track':track,'box':np.array([x,20,x+15,80]),'score':.9,
            'feature':np.asarray(feature if feature is not None else [1.,0.,0.])}


def establish(memory,items,start=0):
    memory.update(items,start,(480,640,3))
    return memory.update(items,start+.2,(480,640,3))


def test_five_moved_then_five_revealed_count_ten(memory):
    first = [item(i,i*30) for i in range(1,6)]
    establish(memory,first)
    assert memory.total == 5
    moved = [item(i,300+i*30) for i in range(1,6)]
    memory.update(moved,.4,(480,640,3))
    assert memory.total == 5
    # Even identical appearance at the exact old locations represents NEW
    # objects when the old five are simultaneously visible elsewhere.
    behind = [item(i+5,i*30) for i in range(1,6)]
    establish(memory,moved+behind,.6)
    assert memory.total == 10
    for stamp in np.arange(1.,5.,.2):
        memory.update(moved+behind,float(stamp),(480,640,3))
    assert memory.total == 10


def test_lost_track_gets_review_not_automatic_duplicate(memory):
    establish(memory,[item(1)])
    memory.update([],.4,(480,640,3))
    out = establish(memory,[item(21,200)],.6)
    assert memory.total == 1
    assert out[0]['state'] == 'review'
    assert memory.resolve(21,existing_id=1)
    memory.update([item(21,210)],1.,(480,640,3))
    assert memory.total == 1


def test_operator_can_confirm_similar_new_roll(memory):
    establish(memory,[item(1)])
    establish(memory,[item(2)],.4)
    assert memory.total == 1
    assert memory.resolve(2)
    assert memory.total == 2


def test_simultaneous_objects_cannot_share_identity(memory):
    establish(memory,[item(1)])
    establish(memory,[item(2)],.4)
    assert 2 in memory.candidates
    memory.visible_ids.add(1)
    assert not memory.resolve(2,existing_id=1)


def test_restart_keeps_count_and_requires_review(memory):
    establish(memory,[item(1)])
    restarted = Memory(memory.store,confirm_frames=2,confirm_seconds=.1)
    assert restarted.total == 1
    establish(restarted,[item(1)],1.)
    assert restarted.total == 1
    assert 1 in restarted.candidates


def test_long_frame_gap_invalidates_tracker_bindings(memory):
    establish(memory,[item(1)])
    establish(memory,[item(1)],10.)
    assert memory.total == 1
    assert 1 in memory.candidates


def test_slow_cpu_with_known_camera_continuity_still_confirms(memory):
    memory.update([item(1)],0.,(480,640,3),continuity_known=True)
    memory.update([item(1)],4.,(480,640,3),continuity_known=True)
    assert memory.total == 1
    memory.update([item(1)],8.,(480,640,3),continuity_known=True)
    assert memory.total == 1


def test_zone_controls_birth_not_following(memory):
    memory.zone = [0,0,.3,1]
    establish(memory,[item(1,500)])
    assert memory.total == 0
    establish(memory,[item(1,30)],.4)
    assert memory.total == 1
    establish(memory,[item(1,500)],.8)
    assert memory.total == 1


def test_ignored_false_detection_is_not_counted(memory):
    establish(memory,[item(1)])
    establish(memory,[item(2)],.4)
    assert memory.resolve(2,ignore=True)
    establish(memory,[item(2)],.8)
    assert memory.total == 1


def test_capacity_does_not_silently_forget_old_items(memory):
    memory.capacity = 1
    establish(memory,[item(1)])
    establish(memory,[item(1),item(2,100)],.4)
    assert memory.total == 1
    assert memory.warning


def test_reset_is_explicit_and_preserves_audit(memory):
    establish(memory,[item(1)])
    memory.store.reset()
    reset = Memory(memory.store)
    assert reset.total == 0
    kinds = [row[0] for row in memory.store.db.execute('SELECT kind FROM events')]
    assert kinds == ['COUNT','RESET']


def test_export_unicode_csv(memory,tmp_path):
    establish(memory,[item(1)])
    target = tmp_path/'history.csv'
    memory.store.export(target)
    assert 'Cuộn mới' in target.read_text('utf-8-sig')


def test_first_launch_waits_for_explicit_region(memory):
    memory.enabled = False
    establish(memory,[item(1)])
    assert memory.total == 0
    memory.enabled = True
    memory.update([item(1)],.4,(480,640,3))
    assert memory.total == 1


def test_reset_does_not_reuse_reference_image_ids(memory):
    establish(memory,[item(1)])
    memory.store.reset()
    reset = Memory(memory.store,confirm_frames=2,confirm_seconds=.1)
    establish(reset,[item(1)])
    assert list(reset.records) == [2]
