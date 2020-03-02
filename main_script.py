import os
import time
import re

global lag_threshold
global criteria
global statistic_dict, alarm_dict, result_dict

# Threshold for lag value
lag_threshold = 5000

# When status == pre_alarm we should take 'n' last lines and they should not contain more than 'm' high lag records
# This limits defined by [n, m] list:
criteria = [5, 2]

# Look for new files every 't' seconds
t = 1

inputdir = os.getcwd() + "/Input/"
outputdir = os.getcwd() + "/Output/"


def main_func(file_name):
    global statistic_dict, alarm_dict, result_dict

    # Take a break to see what happen
    # time.sleep(1)

    # Open file using 'with - as'
    with open(inputdir + file_name, 'r') as current_file:
        parsing_status = 'ok'
        statistic_dict = {}
        alarm_dict = {}
        result_dict = {}
        lines_counter = 0
        parser_drop_counter = 0

        for line in current_file:
            # We push string through our parser.
            parsing_result = parser(line.strip())
            lines_counter = lines_counter + 1
            # Make some work if list 'time_plus_lag' not empty
            if parsing_result:
                # DEBUG # print ('PARSER ACCEPT: ' + line.strip())
                # DEBUG # print ('Time-code is: ' + parsing_result[0] + '. Lag time is: ' + parsing_result[1])
                # DEBUG # print ("Lag is over limit!!!" if parsing_result[2] else "Limit not reached.")
                if parsing_status is 'ok':
                    parsing_status = we_in_status_ok(parsing_result)
                elif parsing_status is 'pre_alarm':
                    parsing_status = we_in_status_pre_alarm(parsing_result)
                else:
                    parsing_status = we_in_status_alarm(parsing_result)

            # If parser return nothing (that string of file mismatch with RE) we can do something, or not ))
            else:
                # DEBUG # print ('PARSER DROP: ' + line)
                parser_drop_counter = parser_drop_counter + 1
                pass

        # When lines in file ends we have to make final work
        # DEBUG # print('THE END OF THE FILE. Processing ' + str(lines_counter) + ' line(s). Parser drop ' + str(parser_drop_counter) + ' line(s).')
        # DEBUG # print result_dict

    with open(outputdir + 'result_' + file_name, 'w') as result_file:
        if result_dict:
            result_file.write('# Found some alarms.\n\n#')
            result_file.write('# The following criteria were established:\n')
            result_file.write('# 1) Log was checked with lag threshold (ms) = ' + str(lag_threshold) + '\n')
            result_file.write('# 2) An accident was recorded if the chain of ' + str(criteria[0]) + ' lines had more than ' + str(criteria[1]) + ' "overlags".\n')
            result_file.write('# Format: accident-start-datetime first-logline-datetime accident-end-datetime duration(seconds) logline-chain accident-max-lag\n\n')
            for key in range(1, len(result_dict.keys()) + 1):
                result_file.write(' '.join(result_dict.get(key)) + '\n')
        else:
            result_file.write('# Found no alarms in source log-file.\n')
        result_dict.clear()

    os.remove(inputdir + file_name)


def parser(line):
    # Parser get line and check it for match with RE for DROP lines without needed args, like timestamp ang lag value
    # Parser return empty list if line was DROP.
    # Otherwise parser return list of three params:
    # 1) timestamp from the line /str
    # 2) lag value from the line /str
    # 3) result of compare lag value with threshold: TRUE if lag exceed it /bool

    match = re.search('(^\d{4}(-\d\d){2}\s(\d{2}:?){3})\s.*\s(\d{1,}$)', line)
    if match:
        logline_time = match.group(1)
        lag_value = match.group(4)
        high_lag = False
        if int(lag_value) >= lag_threshold:
            high_lag = True
        return [logline_time, lag_value, high_lag]
    else:
        return []


def we_in_status_ok(parsing_result):
    global statistic_dict
    # If lag is beyond lag_threshold, then change status:
    if parsing_result[2]:
        statistic_dict = {1: parsing_result}
        # DEBUG # print statistic_dict
        # DEBUG # print ('Changing status to PRE_ALARM!')
        return 'pre_alarm'
    # If everything is fine, then just do nothing
    else:
        return 'ok'


def we_in_status_pre_alarm(parsing_result):
    global statistic_dict, alarm_dict
    count_not_ok = int(max(statistic_dict.keys())) + 1
    # DEBUG # print ('Count_not_ok for now = ' + str(count_not_ok))
    statistic_dict[count_not_ok] = parsing_result
    # DEBUG # print statistic_dict

    if count_not_ok >= criteria[0]:
        # Getting quantity of lines with high lag for some last lines (criteria[0]):
        number_of_overlags = overlimits_lags_counter(count_not_ok, statistic_dict)

        if number_of_overlags == 0:
            # We can change status to OK
            # DEBUG # print ('Changing status to OK! :)')
            return 'ok'
        elif number_of_overlags <= criteria[1]:
            # We should keep status PRE_ALARM and wait new lines
            # DEBUG # print ('Keep status PRE_ALARM...')
            return 'pre_alarm'
        else:
            # Too much overlags, changing status to ALARM
            # DEBUG # print ('Changing status to ALARM!!!')
            # Need find start of ALARM - first line with high lag in last (criteria[0]) lines:
            for i in range(count_not_ok - criteria[0] + 1, count_not_ok + 1):
                if statistic_dict.get(i)[2]:
                    alarm_start = i
                    break
            # DEBUG # print ('alarm_start = ' + str(alarm_start))

            # Fill alarm_dict:
            alarm_dict = statistic_dict.copy()
            for key in range(1, alarm_start):
                # DEBUG # print ('key = ' + str(key))
                del alarm_dict[key]
            if not alarm_dict.get(1):
                for another_key in range(alarm_start, len(statistic_dict) + 1):
                    alarm_dict[another_key - alarm_start + 1] = alarm_dict.pop(another_key)

            # Clear statistic_dict:
            statistic_dict.clear()

            # DEBUG # print ('Alarm_dict:')
            # DEBUG # print alarm_dict
            # DEBUG # print ('Statistic_dict (should be empty):')
            # DEBUG # print statistic_dict

            return 'alarm'

    else:
        # Status PRE_ALARM, but there are not enough lines to decision.
        return 'pre_alarm'


def we_in_status_alarm(parsing_result):
    global alarm_dict, result_dict
    count_not_ok = int(max(alarm_dict.keys())) + 1
    # DEBUG # print ('Count for now = ' + str(count_not_ok))
    alarm_dict[count_not_ok] = parsing_result
    # DEBUG # print statistic_dict

    if count_not_ok >= criteria[0]:

        # Getting quantity of lines with high lag for some last lines (criteria[0]):
        number_of_overlags = overlimits_lags_counter(count_not_ok, alarm_dict)

        if number_of_overlags > criteria[1]:
            # Quantity of overlags too high - keep status ALARM.
            # DEBUG # print ('Keep status ALARM!')
            return 'alarm'
        else:
            # Alarm is over.

            # DEBUG # print ('\nAlarm is over. Here is full alarm_dict:')
            # DEBUG # print alarm_dict
            # DEBUG # print ('We will check next range of dict for cutting:')
            # DEBUG # print range(len(alarm_dict), len(alarm_dict) - criteria[0], -1)

            # Cut good lines from the end of alarm_dict.
            for i in range(len(alarm_dict), len(alarm_dict) - criteria[0], -1):

                if not alarm_dict.get(i)[2]:
                    del alarm_dict[i]
                else:
                    break

            # DEBUG # print ('And here is cuted alarm_dict:')
            # DEBUG # print ('\n')
            # DEBUG # print alarm_dict

            # We need to find time of incident, it duration, quantity of respective lines in log and max value of lag

            calc_start_time_list = []
            calc_max_lag_list = []
            for key in alarm_dict.keys():
                calc_start_time_list.append(datetime_to_timestamp(alarm_dict.get(key)[0]) - int(alarm_dict.get(key)[1]) / 1000)
                calc_max_lag_list.append(int(alarm_dict.get(key)[1]))

            incident_begin = timestamp_to_datetime(min(calc_start_time_list))
            incident_first_logline = alarm_dict.get(1)[0]
            incident_end = alarm_dict.get(len(alarm_dict))[0]
            incident_duration = datetime_to_timestamp(incident_end) - datetime_to_timestamp(incident_begin)
            incident_chain = len(alarm_dict)
            incident_max_lag = max(calc_max_lag_list)

            # We need to write statistics about it.
            # DEBUG # print ('__________WRITING SOME STATISTIC ABOUT ALARM__________')
            # DEBUG # print ('incident_begin ' + incident_begin)
            # DEBUG # print ('incident_first_logline ' + incident_first_logline)
            # DEBUG # print ('incident_end ' + incident_end)
            # DEBUG # print ('incident_duration ' + str(incident_duration))
            # DEBUG # print ('incident_chain ' + str(incident_chain))
            # DEBUG # print ('incident_max_lag ' + str(incident_max_lag))

            if not result_dict:
                result_count = 1
            else:
                result_count = int(max(result_dict.keys())) + 1
            result_dict[result_count] = [incident_begin, incident_first_logline, incident_end, str(incident_duration), str(incident_chain), str(incident_max_lag)]

            # Clear alarm_dict:
            alarm_dict.clear()
            # DEBUG # print ('Changing status to OK :))))')
            return 'ok'
    else:
        # Still ALARM because there are not enough lines to decision.
        return 'alarm'


def overlimits_lags_counter(count_not_ok, dict_to_count):
    # Let`s count number of overlimits lags for some last lines (which set by criteria[0])
    keys_to_request = range((count_not_ok + 1 - criteria[0]), (count_not_ok + 1))
    number_of_overlags = 0
    for i in keys_to_request:
        if dict_to_count.get(i)[2]:
            number_of_overlags = number_of_overlags + 1
    # DEBUG # print ('Overlags = ' + str(number_of_overlags))
    return number_of_overlags


def datetime_to_timestamp(datestr):
    timestampstr = int(time.mktime(time.strptime(datestr, "%Y-%m-%d %H:%M:%S")))
    return timestampstr


def timestamp_to_datetime(timestampstr):
    datestr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestampstr))
    return datestr


# It is endless cycle, that check Input folder
while True:
    # DEBUG # print('\n------------------------------\nNew iteration\n------------------------------\n')
    files_list = os.listdir(inputdir)
    for single_file in files_list:
        if single_file is not None:
            # DEBUG # print('Find some files in Input: ' + single_file)
            main_func(single_file)
    time.sleep(t)
