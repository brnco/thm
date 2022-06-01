'''
handles mediaconch file validation
'''
import pathlib
import util
import subprocess

def load_mediaconch_policies(kwargs):
    '''
    loads policies from folder in config file
    '''
    true_parent = kwargs.config.mediaconchas
    childs = true_parent.glob('**/*.xml')
    mediaconch_policies = []
    for child in childs:
        if str(child.parent) == str(true_parent):
            mediaconch_policies.append(child)
    if not mediaconch_policies:
        print("ERROR: no mediaconch policies found at config path: " + str(kwargs.config.mediaconchas))
        return False
    return mediaconch_policies

def validate_output(accession, files, kwargs):
    '''
    validates output video files
    '''

def validate_input(accession, files, kwargs):
    '''
    validates input video files
    '''
    if not kwargs.accession_mediaconch_policy:
        mediaconch_policies = load_mediaconch_policies(kwargs)
    else:
        mediaconch_policies = [kwargs.accession_mediaconch_policy]
    policy_passes = []
    logs = []
    for policy in mediaconch_policies:
        for file in files:
            print("testing " + str(file) + " against " + str(policy))
            output = subprocess.run(['mediaconch','-p',policy,file], capture_output=True)
            print(output.returncode)
            print(output.stdout)
            print(output.stderr)
            if not output.returncode == 0:
                logs.append("ERROR: mediaconch returned a non-zero exit code")
                return False, logs
            elif not "pass" in str(output.stdout):
                logs.append("ERROR: mediaconch input validation failed for: " + str(file))
                logs.append(str(output.stdout))
                return False, logs
            else:
                logs.append("INFO: mediaconch input validation passed for: " + str(file))
                logs.append(str(output.stdout))
                policy_passes.append(file)
        if policy_passes:
            logs.append("INFO: mediaconch input validation passed for " + str(accession))
            logs.append("INFO: input/output mediaconch policy is " + str(policy))
            accession_mediaconch_policy = policy
            return accession_mediaconch_policy, logs
        else:
            continue
    logs.append("ERROR: mediaconch unable to pass input validation for accession " + str(accession))
    return False, logs

def main():
    '''
    do the thing
    '''

if __name__ == "__main__":
    main()
