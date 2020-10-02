# please import pandas, requiests and yaml
# This works with python3 
import argparse
import pandas as pd
import requests
import sys
import yaml

# format API response body to appropriate form
# If you want to change the csv data, modify this function
def formatData(reponse_body):
    headers = ['login', 'firstName', 'lastName', 'status', 'lastLogin']
    data = list(map(lambda x: [
                                x['profile']['login'], # necessary
                                x['profile']['firstName'],
                                x['profile']['lastName'],
                                x['status'], # necessary
                                x['lastLogin']
                              ], reponse_body))
    return data, headers


def list_groupMembersById(groupId, outputfileName, okta_domain, okta_apikey, all_flag=False):
    url = 'https://' + okta_domain + '.okta.com/api/v1/groups/' + groupId + '/users'
    headers = {
        'content-type': 'application/json',
        'Authorization': 'SSWS ' + okta_apikey
    }

    response = requests.get(url=url, headers=headers)
    if response.status_code == 200:
        response_json = response.json()
        formatted_data, formatted_headers = formatData(response_json)
        df = pd.DataFrame(
            formatted_data,
            columns=formatted_headers
        )

        response_links = requests.utils.parse_header_links(response.headers['Link'].rstrip('>').replace('>,<', ',<'))
        next_url = ''
        next = False
        for linkobj in response_links:
            if linkobj['rel'] == 'next':
                next_url = linkobj['url']
                next = True
            else:
                next = False

        # if there still exits users, get next data
        while next:
            response = requests.get(url=next_url, headers=headers)
            if response.status_code == 200:
                response_json = response.json()
                formatted_data, formatted_headers = formatData(response_json)
                df2 = pd.DataFrame(
                    formatted_data,
                    columns=formatted_headers
                )
                df.append(df2, ignore_index=True)

                response_links = requests.utils.parse_header_links(response.headers['Link'].rstrip('>').replace('>,<', ',<'))
                next_url = ''
                for linkobj in response_links:
                    if linkobj['rel'] == 'next':
                        next_url = linkobj['url']
                        next = True
                    else:
                        next = False

        # if all = Ture, return all / else return except deactivated users
        if (not all_flag):
            df = df[df['status'] != 'DEPROVISIONED']

        print('The member count : ' + str(df['status'].size))

        # export to csv
        filePath = './' + outputfileName
        df.to_csv(filePath, index=False)
        print('Group members are successfully exported to ' + filePath)
        return

    else:
        print("Unhandled Error:")
        raise Exception(response.json())


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
        description='Get Users from specific group'
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
        '-o',
        '--output',
        metavar="OutputFile",
        default="groupmember",
        type=str,
        help='Output File Name. If you configure this as "test" then the name of output file will be "test.csv"'
    )
    parser.add_argument(
        '-a',
        '--all',
        action='store_true',
        help='Return all (including Deactivated) members. (By Default, Deactivated users are not returned)'
    )
    
    args = parser.parse_args()
    if (not args.id and not args.name or args.id and args.name):
        print('you need to configure one of the --name or --id option (and just one option)')
        sys.exit()

    fileName = args.output + ".csv"

    # load variables
    # variables:
    #   okta_domain : The domain of your Okta. If your Okta sign-in url is "https://hoge.okta.com" then this should be "hoge"
    #   okta_apikey : The api key created by admin account. It's better to create by Group membership Admin with all group scope.
    with open(args.env_file) as f:
        env_vars = yaml.safe_load(f)

    okta_domain = env_vars['okta_domain']
    okta_apikey = env_vars['okta_apikey']

    if (args.name):
        try:
            group_id = get_groupIdByName(args.name, okta_domain, okta_apikey)
        except Exception as e:
            print("Something went wrong during getting group id")
            print(e)
            sys.exit()
    else:
        group_id = args.id

    all_flag = args.all

    try:
        list_groupMembersById(group_id, fileName, okta_domain, okta_apikey, all_flag)
        print('Complete.')
    except Exception as e:
        print("Something went wrong during getting group members.")
        print(e)


