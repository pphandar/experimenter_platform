from detection_component import DetectionComponent
from tornado import gen
import math
from utils import *
import geometry
import time
import params
import numpy as np
from emdat_utils import *
import ast

class EMDATComponent(DetectionComponent):

    def  __init__(self, tobii_controller, adaptation_loop, callback_time):
        DetectionComponent.__init__(self, tobii_controller, adaptation_loop, is_periodic = True, callback_time = callback_time)
        self.pups_idx   = 0
        self.pupv_idx   = 0
        self.dist_idx   = 0
        self.fix_idx    = 0
        self.x_y_idx    = 0
        self.id = 1
        self.AOIS = self.application_state_controller.getEmdatAoiMapping()
        print(self.AOIS)
        print("NUMBER OF AOIS %d" % len(self.AOIS))
        self.emdat_task_features = {}
        self.init_emdat_features(self.emdat_task_features)
        self.tobii_controller.update_aoi_storage(self.AOIS)
        self.feature_select = self.application_state_controller.getEdmatFeatures()
        self.execfile = open('newfile.txt', 'w')

    def notify_app_state_controller(self):
        """
        Selects features for specified events in Application State and sends them to the database.
        """
        self.application_state_controller.updateEmdatTable(self.id, self.select_features())

    def select_features(self):
        features_to_send = {}
        for event_name, feature_name in self.feature_select.iteritems():
            if self.AOIS[event_name] == []:
                features_to_send[event_name] = (self.emdat_interval_features[feature_name],
                                                self.emdat_task_features[feature_name],
                                                self.tobii_controller.emdat_global_features[feature_name])
            else:
                print event_name
                print feature_name
                print("interval feature: %f" % self.emdat_interval_features[event_name][feature_name])
                print ("task feature: %f" % self.emdat_task_features[event_name][feature_name])
                print ("global feature: %f" % self.tobii_controller.emdat_global_features[event_name][feature_name])
                print
                features_to_send[event_name] = (self.emdat_interval_features[event_name][feature_name],
                                                self.emdat_task_features[event_name][feature_name],
                                                self.tobii_controller.emdat_global_features[event_name][feature_name])
        return features_to_send

    @gen.coroutine
    def run(self):
        """
        Calculates the features for new raw Tobii data collected since
        the last call to EMDAT Component, merges it with previously computed
        features and sends the results to the Application State.
        """
        start_time = time.time()
        self.start = self.tobii_controller.time[self.pups_idx]
        self.end = self.tobii_controller.time[-1]
        self.length = self.end - self.start
        self.calc_validity_gaps()
        self.emdat_interval_features = {}
        self.init_emdat_features(self.emdat_interval_features)
        self.length_invalid = self.get_length_invalid()
        self.emdat_interval_features['length'] = self.length
        self.emdat_interval_features['length_invalid'] = self.length_invalid

        """ calculate pupil dilation features """
        pupil_start_time = time.time()
        #print("\n\n\n============ START calculating features for whole screen ============")
        if (params.USE_PUPIL_FEATURES):
            self.calc_pupil_features()
        #print("Calculating PUPIL features for WHOLE screen: --- %s seconds ---" % (time.time() - pupil_start_time))
        """ calculate distance from screen features"""
        if (params.USE_DISTANCE_FEATURES):
            self.calc_distance_features()
        """ calculate fixations, angles and path features"""
        if (params.USE_FIXATION_PATH_FEATURES):
            self.calc_fix_ang_path_features()
        #print("Calculating FIXATION ANGLE features for WHOLE screen: --- %s seconds ---" % (time.time() - fix_angle_start_time))
        #print("============ FINISH calculating features for whole screen ============\n\n\n\n\n")

        all_aoi_time = time.time()
        #print(all_aoi_time)
        """ calculate AOIs features """
        #print("============ START calculating features for AOIS ============\n\n")

        self.calc_aoi_features()# rest_pupil_size, export_pupilinfo)
        #print("============ FINISH calculating features for AOIS ============\n\n\n\n\n")
        #print(time.time())
        #print(time.time() - all_aoi_time)
        #print("Calculating ALL AOI: --- %s seconds ---" % (time.time() - all_aoi_time))
        all_merging_time = time.time()
        if (params.KEEP_TASK_FEATURES and params.KEEP_GLOBAL_FEATURES):
            self.merge_features(self.emdat_interval_features, self.emdat_task_features)
            self.merge_features(self.emdat_interval_features, self.tobii_controller.emdat_global_features)
        elif (params.KEEP_TASK_FEATURES):
            self.merge_features(self.emdat_interval_features, self.emdat_task_features)
        elif (params.KEEP_GLOBAL_FEATURES):
            self.merge_features(self.emdat_interval_features, self.tobii_controller.emdat_global_features)
        print("Complete EMDAT execution --- %.12f seconds --- \n\n\n" % (time.time() - start_time))
        self.execfile.write("%.5f\n" % (time.time() - start_time))
        print self.id
        self.id += 1
        self.notify_app_state_controller()

    def init_emdat_features(self, features_dictionary):
        """
        Initializes the given feature dictionary with empty values.
        """
        features_dictionary['length'] = 0
        features_dictionary['length_invalid'] = 0
		# Pupil features
        features_dictionary['numpupilsizes']    	    = 0
        features_dictionary['numpupilvelocity']		= 0
        features_dictionary['meanpupilsize'] 			= -1
        features_dictionary['stddevpupilsize'] 		= -1
        features_dictionary['maxpupilsize'] 			= -1
        features_dictionary['minpupilsize'] 			= -1
        features_dictionary['startpupilsize'] 			= -1
        features_dictionary['endpupilsize'] 			= -1
        features_dictionary['meanpupilvelocity'] 		= -1
        features_dictionary['stddevpupilvelocity'] 	= -1
        features_dictionary['maxpupilvelocity'] 		= -1
        features_dictionary['minpupilvelocity'] 		= -1
        features_dictionary['startpupilvelocity'] 		= -1
        features_dictionary['endpupilvelocity'] 		= -1

		# Distance features
        features_dictionary['numdistancedata']			= 0
        features_dictionary['meandistance'] 			= -1
        features_dictionary['stddevdistance'] 			= -1
        features_dictionary['maxdistance'] 			= -1
        features_dictionary['mindistance'] 			= -1
        features_dictionary['startdistance'] 			= -1
        features_dictionary['enddistance'] 				= -1
		# Path features
        features_dictionary['numfixdistances'] 		= 0
        features_dictionary['numabsangles'] 			= 0
        features_dictionary['numrelangles'] 			= 0
        features_dictionary['meanpathdistance'] 		= -1
        features_dictionary['sumpathdistance'] 		= -1
        features_dictionary['stddevpathdistance'] 		= -1
        features_dictionary['eyemovementvelocity'] 	= -1
        features_dictionary['sumabspathangles'] 		= -1
        features_dictionary['abspathanglesrate'] 		= -1
        features_dictionary['meanabspathangles']		= -1
        features_dictionary['stddevabspathangles']		= -1
        features_dictionary['sumrelpathangles'] 		= -1
        features_dictionary['relpathanglesrate'] 		= -1
        features_dictionary['meanrelpathangles']		= -1
        features_dictionary['stddevrelpathangles']     = -1
		# Fixation features
        features_dictionary['numfixations'] 			= 0
        features_dictionary['fixationrate'] 			= -1
        features_dictionary['meanfixationduration'] 	= -1
        features_dictionary['stddevfixationduration'] 	= -1
        features_dictionary['sumfixationduration'] 	= -1
        features_dictionary['fixationrate'] 			= -1
        for aoi in self.AOIS.keys():
            features_dictionary[aoi] = {}
            features_dictionary[aoi]['numfixations'] 			    = 0
            features_dictionary[aoi]['longestfixation']            = -1
            features_dictionary[aoi]['meanfixationduration']       = -1
            features_dictionary[aoi]['stddevfixationduration']     = -1
            #features_dictionary[aoi]['timetofirstfixation']        = -1
            #features_dictionary[aoi]['timetolastfixation']         = -1
            features_dictionary[aoi]['proportionnum']              = 0
            features_dictionary[aoi]['proportiontime']             = 0
            features_dictionary[aoi]['fixationrate']               = 0
            features_dictionary[aoi]['totaltimespent']             = 0
            features_dictionary[aoi]['meanpupilsize']              = -1
            features_dictionary[aoi]['stddevpupilsize']            = -1
            features_dictionary[aoi]['maxpupilsize']               = -1
            features_dictionary[aoi]['minpupilsize']               = -1
            features_dictionary[aoi]['startpupilsize']             = -1
            features_dictionary[aoi]['endpupilsize']               = -1
            features_dictionary[aoi]['startpupilvelocity']             = -1
            features_dictionary[aoi]['endpupilvelocity']               = -1

            features_dictionary[aoi]['meanpupilvelocity']          = -1
            features_dictionary[aoi]['stddevpupilvelocity']        = -1
            features_dictionary[aoi]['maxpupilvelocity']           = -1
            features_dictionary[aoi]['minpupilvelocity']           = -1
            features_dictionary[aoi]['numpupilsizes']              = 0
            features_dictionary[aoi]['numpupilvelocity']           = 0
            features_dictionary[aoi]['numdistancedata']            = 0
            features_dictionary[aoi]['numdistancedata']            = 0
            features_dictionary[aoi]['meandistance']               = -1
            features_dictionary[aoi]['stddevdistance']             = -1
            features_dictionary[aoi]['maxdistance']                = -1
            features_dictionary[aoi]['mindistance']                = -1
            features_dictionary[aoi]['startdistance']              = -1
            features_dictionary[aoi]['enddistance']                = -1
            features_dictionary[aoi]['total_trans_from']           = 0

            for cur_aoi in self.AOIS.keys():
                features_dictionary[aoi]['numtransfrom_%s'%(cur_aoi)] = 0
                features_dictionary[aoi]['proptransfrom_%s'%(cur_aoi)] = -1

    def merge_features(self, part_features, accumulator_features):
        """
        Merges features from two dictionaries into accumulator_features.
        Usually called with emdat_interval_features as part_features and with
        emdat_task_features or emdat_global_features as accumulator_features
        """
        accumulator_features['length'] = sumfeat(part_features, accumulator_features, "['length']")
        accumulator_features['length_invalid'] = sumfeat(part_features, accumulator_features, "['length_invalid']")

        if (params.USE_PUPIL_FEATURES):
            merge_pupil_features(part_features, accumulator_features)
            for aoi in self.AOIS.keys():
                if (len(self.tobii_controller.aoi_ids[aoi]) > 0):
                    merge_pupil_features(part_features[aoi], accumulator_features[aoi])
        """ calculate distance from screen features"""
        if (params.USE_DISTANCE_FEATURES):
            merge_distance_features(part_features, accumulator_features)
            for aoi in self.AOIS.keys():
                if (len(self.tobii_controller.aoi_ids[aoi]) > 0):
                    merge_distance_features(part_features[aoi], accumulator_features[aoi])

        """ calculate fixations, angles and path features"""
        if (params.USE_FIXATION_PATH_FEATURES):
            merge_path_angle_features(part_features, accumulator_features)
            merge_fixation_features(part_features, accumulator_features)
            for aoi in self.AOIS.keys():
                if (len(self.tobii_controller.aoi_ids[aoi]) > 0):
                    merge_aoi_fixations(part_features[aoi], accumulator_features[aoi], accumulator_features['length'], accumulator_features['numfixations'])
                    if (params.USE_TRANSITION_AOI_FEATURES):
                        if (len(self.tobii_controller.aoi_ids[aoi]) > 0):
                            merge_aoi_transitions(part_features[aoi], accumulator_features[aoi])

    def calc_pupil_features(self):
        """
		 Called from run(). Calculates pupil features for the whole screen with new raw
         Tobii datapoints generated since the last call to run(). Features are stored in emdat_interval_features.
         """
        valid_pupil_data = []
        while(self.pups_idx < len(self.tobii_controller.pupilsize)):
            if (self.tobii_controller.pupilsize[self.pups_idx] > 0):
                valid_pupil_data.append(self.tobii_controller.pupilsize[self.pups_idx])
            self.pups_idx += 1
        valid_pupil_velocity = []
        while(self.pupv_idx < len(self.tobii_controller.pupilvelocity)):
            if (self.tobii_controller.pupilvelocity[self.pupv_idx] != -1):
                valid_pupil_velocity.append(self.tobii_controller.pupilvelocity[self.pupv_idx])
            self.pupv_idx += 1
        #number of valid pupil sizes
        self.emdat_interval_features['numpupilsizes']           = len(valid_pupil_data)
        self.emdat_interval_features['numpupilvelocity']        = len(valid_pupil_velocity)

        if self.emdat_interval_features['numpupilsizes'] > 0: #check if the current segment has pupil data available
            if params.PUPIL_ADJUSTMENT == "rpscenter":
                adjvalidpupilsizes = map(lambda x: x- params.REST_PUPIL_SIZE, valid_pupil_data)
            elif params.PUPIL_ADJUSTMENT == "PCPS":
                adjvalidpupilsizes = map(lambda x: (x - params.REST_PUPIL_SIZE) / (1.0 * params.REST_PUPIL_SIZE), valid_pupil_data)
            else:
                adjvalidpupilsizes = map(lambda x: x, valid_pupil_data)#valid_pupil_data
            self.emdat_interval_features['meanpupilsize']           = mean(valid_pupil_data)
            self.emdat_interval_features['stddevpupilsize']         = stddev(valid_pupil_data)
            self.emdat_interval_features['maxpupilsize']            = max(valid_pupil_data)
            self.emdat_interval_features['minpupilsize']            = min(valid_pupil_data)
            self.emdat_interval_features['startpupilsize']          = valid_pupil_data[0]
            self.emdat_interval_features['endpupilsize']            = valid_pupil_data[-1]

            if len(valid_pupil_velocity) > 0:
                self.emdat_interval_features['meanpupilvelocity']   = mean(valid_pupil_velocity)
                self.emdat_interval_features['stddevpupilvelocity'] = stddev(valid_pupil_velocity)
                self.emdat_interval_features['maxpupilvelocity']    = max(valid_pupil_velocity)
                self.emdat_interval_features['minpupilvelocity']    = min(valid_pupil_velocity)
                self.emdat_interval_features['startpupilvelocity']  = valid_pupil_velocity[0]
                self.emdat_interval_features['endpupilvelocity']    = valid_pupil_velocity[-1]

    def calc_distance_features(self):
        """
        Called from run(). Calculates distance features for the whole screen with new raw
        Tobii datapoints generated since the last call to run(). Features are stored in
        emdat_interval_features.
        """
        #get all datapoints where distance is available
        distances_from_screen = []
        while (self.dist_idx < len( self.tobii_controller.head_distance)):
            if (self.tobii_controller.head_distance[self.dist_idx] > 0):
                distances_from_screen.append(self.tobii_controller.head_distance[self.dist_idx])
            self.dist_idx += 1
        #number of valid distance datapoints
        numdistancedata = len(distances_from_screen)
        if numdistancedata > 0: #check if the current segment has pupil data available
            self.emdat_interval_features['meandistance']       = mean(distances_from_screen)
            self.emdat_interval_features['stddevdistance']     = stddev(distances_from_screen)
            self.emdat_interval_features['maxdistance']        = max(distances_from_screen)
            self.emdat_interval_features['mindistance']        = min(distances_from_screen)
            self.emdat_interval_features['startdistance']      = distances_from_screen[0]
            self.emdat_interval_features['enddistance']        = distances_from_screen[-1]
            self.emdat_interval_features['numdistancedata']    = numdistancedata

    def calc_fix_ang_path_features(self):
        """
		 Called from run(). Calculates fixation, angle and path features for the whole
         screen with new raw Tobii datapoints generated since the last call to run().
         Features are stored in emdat_interval_features.
         """
        fixation_data = self.tobii_controller.EndFixations[self.fix_idx:]
        numfixations = len(fixation_data)
        distances = []
        abs_angles = []
        rel_angles = []
        if numfixations > 0:
            # TODO: Check that
            #self.fixation_start = -1
            #self.fixation_end = -1

            self.emdat_interval_features['meanfixationduration'] = mean(map(lambda x: float(x[2]), fixation_data))
            self.emdat_interval_features['stddevfixationduration'] = stddev(map(lambda x: float(x[2]), fixation_data))
            self.emdat_interval_features['sumfixationduration'] = sum(map(lambda x: x[2], fixation_data))

            self.emdat_interval_features['fixationrate'] = float(numfixations) / (self.length - self.length_invalid)
            distances = calc_distances(fixation_data)
            abs_angles = calc_abs_angles(fixation_data)
            rel_angles = calc_rel_angles(fixation_data)
        else:
            #self.fixation_start = -1
            #self.fixation_end = -1

            self.emdat_interval_features['meanfixationduration'] = -1
            self.emdat_interval_features['stddevfixationduration'] = -1
            self.emdat_interval_features['sumfixationduration'] = -1
            self.emdat_interval_features['fixationrate'] = -1
        self.emdat_interval_features['numfixations'] = numfixations

        numfixdistances = len(distances)
        numabsangles = len(abs_angles)
        numrelangles = len(rel_angles)
        if len(distances) > 0:
            self.emdat_interval_features['meanpathdistance'] = mean(distances)
            self.emdat_interval_features['sumpathdistance'] = sum(distances)
            self.emdat_interval_features['stddevpathdistance'] = stddev(distances)
            self.emdat_interval_features['eyemovementvelocity'] = self.emdat_interval_features['sumpathdistance'] / (self.length - self.length_invalid)
            self.emdat_interval_features['sumabspathangles'] = sum(abs_angles)
            self.emdat_interval_features['abspathanglesrate'] = sum(abs_angles)/(self.length - self.length_invalid)
            self.emdat_interval_features['meanabspathangles'] = mean(abs_angles)
            self.emdat_interval_features['stddevabspathangles'] = stddev(abs_angles)
            self.emdat_interval_features['sumrelpathangles'] = sum(rel_angles)
            self.emdat_interval_features['relpathanglesrate'] = sum(rel_angles)/(self.length - self.length_invalid)
            self.emdat_interval_features['meanrelpathangles'] = mean(rel_angles)
            self.emdat_interval_features['stddevrelpathangles'] = stddev(rel_angles)
            self.emdat_interval_features['numfixdistances'] = numfixdistances
            self.emdat_interval_features['numabsangles'] = numabsangles
            self.emdat_interval_features['numrelangles'] = numrelangles

    def calc_validity_gaps(self):
        """
        Calculates the validity gaps in new raw Tobii data, i.e. segments
        with contiguous invalid datapoints, and stores the time segments for which,
        during platform's execution, the data was invalid.
        """
        time = self.tobii_controller.time
        fixations = self.tobii_controller.EndFixations
        validity = self.tobii_controller.validity
        self.time_gaps = []
        if len(fixations) == 0:
            return time[-1] - time[self.pups_idx]
        dindex = self.pups_idx
        datalen = len(validity)
        while dindex < datalen:
            d = validity[dindex]
            while d is True and (dindex < datalen - 1):
                dindex += 1
                d = validity[dindex]
            if d is not True:
                gap_start = time[dindex]
                while d is not True and (dindex < datalen - 1):
                    dindex += 1
                    d = validity[dindex]
                if time[dindex] - gap_start > params.MAX_SEG_TIMEGAP:
                    self.time_gaps.append((gap_start, time[dindex]))
            dindex += 1

    def calc_aoi_features(self):
        """
        Calculates pupil, distance, fixation and transition features
        for AOIs specified for this task using the helper functions listed below.
        """

        start_constructing_numpy        = time.time()
        x_y_coords                      = np.column_stack((np.array(self.tobii_controller.x[self.x_y_idx:]), np.array(self.tobii_controller.y[self.x_y_idx:])))
        pup_size_vals                   = np.array(self.tobii_controller.pupilsize[self.x_y_idx:])
        pup_vel_vals                    = np.array(self.tobii_controller.pupilvelocity[self.x_y_idx:])
        dist_vals                       = np.array(self.tobii_controller.head_distance[self.x_y_idx:])
        fixation_vals                   = np.asarray(self.tobii_controller.EndFixations[self.fix_idx:])

        for aoi in self.AOIS:
            start_computing_features = time.time()

            ## Indices of x-y array where datapoints are inside the specified AOI
            aoi_dpt_indices = np.array(self.tobii_controller.aoi_ids[aoi])
            aoi_dpt_indices = aoi_dpt_indices[aoi_dpt_indices >= self.x_y_idx]
            valid_indices = aoi_dpt_indices - self.x_y_idx

            if (len(valid_indices) == 0):
                continue

            if params.USE_PUPIL_FEATURES:
                ## Select valid pupil sizes inside the AOI
                print(valid_indices)
                valid_pupil_sizes      = pup_size_vals[valid_indices]
                valid_pupil_sizes      = valid_pupil_sizes[valid_pupil_sizes > 0]
                    ## Select valid velocities inside the AOI
                valid_pupil_vel        = pup_vel_vals[valid_indices]
                valid_pupil_vel        = valid_pupil_vel[valid_pupil_vel != -1]
                self.generate_aoi_pupil_features(aoi, valid_pupil_sizes, valid_pupil_vel)
            if params.USE_DISTANCE_FEATURES:
                ## Select valid head distances inside the AOI
                valid_dist_vals        = dist_vals[valid_indices]
                self.generate_aoi_distance_features(aoi, valid_dist_vals)
            if (len(fixation_vals) == 0):
                continue
            if (params.USE_FIXATION_PATH_FEATURES or params.USE_TRANSITION_AOI_FEATURES):
                valid_fixation_indices = np.where(np.apply_along_axis(datapoint_inside_aoi, 1, fixation_vals[:, :2], poly = self.AOIS[aoi]))
            if (params.USE_FIXATION_PATH_FEATURES):
                valid_fixation_vals    = fixation_vals[valid_fixation_indices]
                self.generate_aoi_fixation_features(aoi, valid_fixation_vals, self.length_invalid, len(fixation_vals))
            if (params.USE_TRANSITION_AOI_FEATURES):
                self.generate_transition_features(aoi, fixation_vals, valid_fixation_indices[0])
        self.x_y_idx = len(self.tobii_controller.x)
        self.fix_idx = len(self.tobii_controller.EndFixations)

    def generate_aoi_pupil_features(self, aoi, valid_pupil_data, valid_pupil_velocity):
        """
        Generates pupil features for given AOI
        """
        valid_pupil_data = valid_pupil_data[valid_pupil_data > 0]
        valid_pupil_velocity = valid_pupil_velocity[valid_pupil_velocity != -1]

        self.emdat_interval_features[aoi]['numpupilsizes']          = len(valid_pupil_data)
        self.emdat_interval_features[aoi]['numpupilvelocity']       = len(valid_pupil_velocity)

        if self.emdat_interval_features[aoi]['numpupilsizes'] > 0: #check if the current segment has pupil data available

            if params.PUPIL_ADJUSTMENT == "rpscenter":
                valid_pupil_data        = valid_pupil_data - params.REST_PUPIL_SIZE
            elif params.PUPIL_ADJUSTMENT == "PCPS":
                adjvalidpupilsizes      = (valid_pupil_data - params.REST_PUPIL_SIZE) / (1.0 * params.REST_PUPIL_SIZE)
            else:
                adjvalidpupilsizes      = valid_pupil_data
            self.emdat_interval_features[aoi]['meanpupilsize']              = np.mean(adjvalidpupilsizes)
            self.emdat_interval_features[aoi]['stddevpupilsize']            = calc_aoi_std_feature(adjvalidpupilsizes)
            self.emdat_interval_features[aoi]['maxpupilsize']               = np.max(adjvalidpupilsizes)
            self.emdat_interval_features[aoi]['minpupilsize']               = np.min(adjvalidpupilsizes)
            self.emdat_interval_features[aoi]['startpupilsize']             = adjvalidpupilsizes[0]
            self.emdat_interval_features[aoi]['endpupilsize']               = adjvalidpupilsizes[-1]

            if self.emdat_interval_features[aoi]['numpupilvelocity'] > 0:
                self.emdat_interval_features[aoi]['meanpupilvelocity']      = np.mean(valid_pupil_velocity)
                self.emdat_interval_features[aoi]['stddevpupilvelocity']    = calc_aoi_std_feature(valid_pupil_velocity)
                self.emdat_interval_features[aoi]['maxpupilvelocity']       = np.max(valid_pupil_velocity)
                self.emdat_interval_features[aoi]['minpupilvelocity']       = np.min(valid_pupil_velocity)
                self.emdat_interval_features[aoi]['startpupilvelocity']     = valid_pupil_velocity[0]
                self.emdat_interval_features[aoi]['endpupilvelocity']       = valid_pupil_velocity[-1]

    def generate_aoi_distance_features(self, aoi, valid_distance_data):
        """
        Generates distance features for given AOI
        """
        valid_distance_data = valid_distance_data[valid_distance_data > 0]
        self.emdat_interval_features[aoi]['numdistancedata']        = len(valid_distance_data)
        if self.emdat_interval_features[aoi]['numdistancedata'] > 0:
            self.emdat_interval_features[aoi]['meandistance']       = np.mean(valid_distance_data)
            self.emdat_interval_features[aoi]['stddevdistance']     = calc_aoi_std_feature(valid_distance_data)
            self.emdat_interval_features[aoi]['maxdistance']        = np.max(valid_distance_data)
            self.emdat_interval_features[aoi]['mindistance']        = np.min(valid_distance_data)
            self.emdat_interval_features[aoi]['startdistance']      = valid_distance_data[0]
            self.emdat_interval_features[aoi]['enddistance']        = valid_distance_data[-1]

    def generate_aoi_fixation_features(self, aoi, fixation_data, sum_discarded, num_all_fixations):
        """
        Generates fixation features for given AOI
        """
        numfixations                                                    = len(fixation_data)
        self.emdat_interval_features[aoi]['numfixations']               = numfixations
        fixation_durations                                              = fixation_data[:, 2]
        totaltimespent                                                  = np.sum(fixation_durations)
        self.emdat_interval_features[aoi]['totaltimespent']             = totaltimespent
        self.emdat_interval_features[aoi]['proportiontime']             = float(totaltimespent) / (self.length - self.length_invalid)
        if numfixations > 0:
            self.emdat_interval_features[aoi]['longestfixation']        = np.max(fixation_durations)
            self.emdat_interval_features[aoi]['meanfixationduration']   = np.mean(fixation_durations)
            self.emdat_interval_features[aoi]['stddevfixationduration'] = calc_aoi_std_feature(fixation_durations)
            #self.emdat_interval_features[aoi]['timetofirstfixation']    = fixation_data[0][3] - self.starttime
            #self.emdat_interval_features[aoi]['timetolastfixation']     = fixation_data[-1][3] - self.starttime
            self.emdat_interval_features[aoi]['proportionnum']          = float(numfixations)/num_all_fixations
            self.emdat_interval_features[aoi]['fixationrate']           = numfixations / float(totaltimespent)

    def generate_transition_features(self, cur_aoi, fixation_data, fixation_indices):
        """
        Generates distance features for given AOI
        """
        for aoi in self.AOIS.keys():
            self.emdat_interval_features[cur_aoi]['numtransfrom_%s'%(aoi)] = 0

        sumtransfrom = 0
        for i in fixation_indices:
            if i > 0:
                for aoi in self.AOIS:
                    key = 'numtransfrom_%s'%(aoi)
                    if utils.point_inside_polygon(fixation_data[i-1][0], fixation_data[i-1][1], self.AOIS[aoi]):
                        self.emdat_interval_features[cur_aoi][key] += 1
                        sumtransfrom += 1
        for aoi in self.AOIS.keys():
            if sumtransfrom > 0:
                val = self.emdat_interval_features[cur_aoi]['numtransfrom_%s'%(aoi)]
                self.emdat_interval_features[cur_aoi]['proptransfrom_%s'%(aoi)] = float(val) / sumtransfrom
            else:
                self.emdat_interval_features[cur_aoi]['proptransfrom_%s'%(aoi)] = 0
        self.emdat_interval_features[cur_aoi]['total_trans_from']               = sumtransfrom

    def get_length_invalid(self):
        """
        Takes the result of calc_validity_gaps() to calculate the sum of lengths of invalid segments.
        """
        time = self.tobii_controller.time
        length = 0
        if isinstance(self.time_gaps, list):
            for gap in self.time_gaps:
                length += gap[1] - gap[0]
        else:
            length = time[-1] - time[self.pups_idx]
        return length

def calc_aoi_std_feature(data):
    if (len(data) > 1):
        return np.std(data, ddof = 1)
    else:
        return -1
