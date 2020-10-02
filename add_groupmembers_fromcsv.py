# please import pandas, requiests, yaml and pprint
# This works with python3 
import argparse
import pandas as pd
import requests
import sys
import yaml
import pprint


def add_groupMembersById(groupId, source_list, okta_domain, okta_apikey):

    success_summary = []
    error_summary = []

    for user in source_list:
        getid_url = 'https://' + okta_domain + '.okta.com/api/v1/users/' + user
        getid_headers = {
            'content-type': 'application/json',
            'Authorization': 'SSWS ' + okta_apikey
        }
        getid_res = requests.get(url=getid_url, headers=getid_headers)
        if getid_res.status_code == 200:
            userid = getid_res.json()['id']
            add_url = 'https://' + okta_domain + '.okta.com/api/v1/groups/' + groupId + '/users/' + userid
            add_headers = {
                'content-type': 'application/json',
                'Authorization': 'SSWS ' + okta_apikey
            }
            add_res = requests.put(url=add_url, headers=add_headers)

            if add_res.status_code == 204:
                print('success : ' + user)
                success_summary.append('success : ' + user)
            else:
                print('error @adding: ' + user)
                print(add_res.json())
                error_summary.append([('error @adding: ' + user), add_res.json()])
            
        else:
            print('error @getting userid: ' + user)
            print(getid_res.json())
            error_summary.append([('error @getting userid: ' + user), getid_res.json()])

    print('success count(including duplication) : ' + str(len(success_summary)))
    print('error count(including duplication) : ' + str(len(error_summary)))
    print(' -- error summary -- ')
    pprint.pprint(error_summary)

    return


def get_groupIdByName(groupName, okta_domain, okta_apikey):
    # seach group by name, get id and after that same as list_groupMemberById
    url = 'https://' + okta_domain + '.okta.com/api/v1/groups?q=' + groupName
    headers = {
        'content-type': 'application/json',
        'Authorization': 'SSWS ' + okta_apikey
    }
    response = requests.get(url=url, headers=headers)
    if (response.status_code == 200):
        response_json = response.json()
        if len(response_json) == 1:
            print('target group is: ' + response_json[0]['profile']['name'])
            return response_json[0]['id']
        elif len(response_json) > 1:
            print('There are more than 1 groups which contains ' + groupName)
            for group in response_json:
                print('Group Name: {}, Group Id: {}'.format(group['profile']['name'], group['id']))
            raise Exception('Please use group ID instead')
        else:
            print('There is no group which contains ' + groupName)
            raise Exception('Please chech the group name')
    else:
        print('Unhandled Error')
        raise Exception(response.json())


if __name__ == '__main__':
    # define argparse
    parser = argparse.ArgumentParser(
        description='Add existing Users to specific group'
    )
    parser.add_argument(
        '--env-file',
        required=True,
        type=str,
        help='Source file that contains environment info. REQUIRED'
    )
    parser.add_argument(
        '--name',
        metavar="GroupName",
        type=str,
        help='Full Quarified Name of Target Group. It should be enclosed by quotes.'
    )
    parser.add_argument(
        '--id',
        metavar="GroupId",
        type=str,
        help='ID of Target Group.'
    )
    parser.add_argument(
        '--source',
        metavar="SourceCSVFile",
        type=str,
        help='Full Quorifiled Source File Name. It should be comma separated & have "email" or "login" column.'
    )
    
    args = parser.parse_args()
    if (not args.id and not args.name or args.id and args.name):
        print('you need to configure one of the --name or --id option (and just one option)')
        sys.exit()

    # load variables
    # variables:
    #   okta_domain : The domain of your Okta. If your Okta sign-in url is "https://hoge.okta.com" then this should be "hoge"
    #   okta_apikey : The api key created by admin account. It's better to create by Group membership Admin with all group scope.
    with open(args.env_file) as f:
        env_vars = yaml.safe_load(f)

    okta_domain = env_vars['okta_domain']
    okta_apikey = env_vars['okta_apikey']

    try:
        df = pd.read_csv(args.source)
        if ('email' in df.keys()):
            target_list = df['email'].dropna().to_list()
        elif ('login' in df.keys()):
            target_list = df['login'].dropna().to_list()
        else:
            print("target file don't have 'email' column. Please check it.")
            sys.exit()

        if (len(target_list) == 0):
            print("source file is empty. Please check it.")
            sys.exit()

    except Exception as e:
        print("Something went wrong during reading source file.")
        print(e)
        sys.exit()

    print("Source count: " + str(len(target_list)))

    if (args.name):
        try:
            group_id = get_groupIdByName(args.name, okta_domain, okta_apikey)
        except Exception as e:
            print("Something went wrong during getting group id.")
            print(e)
            sys.exit()
    else:
        group_id = args.id

    print()
    keyval = input("Continue? (Y/N): ")
    if not (keyval == "Y" or keyval == "y"):
        print("interrupted.")
        sys.exit()

    print()

    try:
        add_groupMembersById(group_id, target_list, okta_domain, okta_apikey)
        print('Complete.')
    except Exception as e:
        print("Something went wrong during adding member to the group.")
        print(e)


