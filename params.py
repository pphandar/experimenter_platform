USE_FIXATION_ALGORITHM = True
USE_EMDAT = True
USE_ML = True
# Features to use
USE_PUPIL_FEATURES = True
USE_DISTANCE_FEATURES = True
USE_FIXATION_PATH_FEATURES = True
USE_TRANSITION_AOI_FEATURES = True

# Sets of features to keep
KEEP_TASK_FEATURES = True
KEEP_GLOBAL_FEATURES = True

#Frequency of ML/EMDAT calls:
EMDAT_CALL_PERIOD = 10000
ML_CALL_PERIOD = 6000000

# Some parameter from EMDAT, ask later
MAX_SEG_TIMEGAP= 10

FIX_MAXDIST = 35
FIX_MINDUR = 100000

rest_pupil_size = 0
PUPIL_ADJUSTMENT = "rpscenter"
