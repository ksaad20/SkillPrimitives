name: place
description: Object is lowered and gripper opens to release.

detection:
  strategy: gripper_opening_transition
  preconditions:
    gripper_state: closed    # gripper[t-1] < 0.5
  transition:
    to: open                 # gripper[t] >= 0.5
  parameters:
    pre_window: 3            # frames before transition
    post_window: 5           # frames after transition
  state_requirements:
    velocity: true           # used for confidence boost
    gripper: true
  confidence:
    base: 0.88
    with_downward_z: 0.95    # z_vel < -0.001
    with_low_z: 0.92         # abs(z_vel) < 0.005

constraints:
  temporal_order: [grasp, lift, transport]
  gripper_must_end: open

natural_language:
  templates:
    - "place the object gently"
    - "place {object} down"
    - "release {object}"
    - "set {object} down gently"
