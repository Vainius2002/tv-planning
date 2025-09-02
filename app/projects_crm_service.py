"""
Service to fetch campaigns and projects from Projects-CRM API
"""
import requests
import logging

logger = logging.getLogger(__name__)

# Configuration
PROJECTS_CRM_API_URL = "http://localhost:5002/api"
PROJECTS_CRM_API_KEY = "projects-api-key"
TIMEOUT = 10


def get_campaigns():
    """Fetch all campaigns from Projects-CRM"""
    try:
        url = f"{PROJECTS_CRM_API_URL}/campaigns"
        headers = {'X-API-Key': PROJECTS_CRM_API_KEY}
        
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        
        if response.status_code == 200:
            campaigns = response.json()
            logger.info(f"Fetched {len(campaigns)} campaigns from Projects-CRM")
            return campaigns
        else:
            logger.error(f"Projects-CRM API error: {response.status_code}")
            return []
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error connecting to Projects-CRM: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching campaigns: {e}")
        return []


def get_campaign(campaign_id):
    """Fetch specific campaign from Projects-CRM"""
    try:
        url = f"{PROJECTS_CRM_API_URL}/campaigns/{campaign_id}"
        headers = {'X-API-Key': PROJECTS_CRM_API_KEY}
        
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Projects-CRM API error for campaign {campaign_id}: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error connecting to Projects-CRM: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching campaign {campaign_id}: {e}")
        return None


def get_projects():
    """Fetch all projects from Projects-CRM"""
    try:
        url = f"{PROJECTS_CRM_API_URL}/projects"
        headers = {'X-API-Key': PROJECTS_CRM_API_KEY}
        
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        
        if response.status_code == 200:
            projects = response.json()
            logger.info(f"Fetched {len(projects)} projects from Projects-CRM")
            return projects
        else:
            logger.error(f"Projects-CRM API error: {response.status_code}")
            return []
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error connecting to Projects-CRM: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching projects: {e}")
        return []


def convert_campaign_for_tv_planner(projects_crm_campaign):
    """Convert Projects-CRM campaign format to TV-Planner format"""
    return {
        'id': f"crm_{projects_crm_campaign['id']}",  # Prefix to avoid conflicts
        'name': f"{projects_crm_campaign['name']} ({projects_crm_campaign['code']})",
        'start_date': projects_crm_campaign['start_date'],
        'end_date': projects_crm_campaign['end_date'],
        'agency': 'Projects-CRM',  # Default agency name
        'client': projects_crm_campaign['client_brand_name'] or 'Unknown Client',
        'product': projects_crm_campaign['project_name'],
        'country': 'Lietuva',  # Default country
        'status': 'active',
        'pricing_list_name': None,
        'source': 'projects_crm',
        'original_id': projects_crm_campaign['id'],
        'project_code': projects_crm_campaign['project_code'],
        'campaign_code': projects_crm_campaign['code']
    }


def get_tv_planner_campaigns():
    """Get campaigns formatted for TV-Planner"""
    campaigns = get_campaigns()
    return [convert_campaign_for_tv_planner(campaign) for campaign in campaigns]


def sync_projects_crm_campaign_to_local(campaign_id):
    """Sync a specific Projects-CRM campaign to local TV-Planner database"""
    from app import models
    
    # Remove 'crm_' prefix to get the actual campaign ID
    if str(campaign_id).startswith('crm_'):
        actual_crm_id = int(campaign_id.replace('crm_', ''))
    else:
        actual_crm_id = int(campaign_id)
    
    # Get the campaign from Projects-CRM
    projects_crm_campaign = get_campaign(actual_crm_id)
    if not projects_crm_campaign:
        raise ValueError(f"Campaign {actual_crm_id} not found in Projects-CRM")
    
    # Convert to TV-Planner format
    tv_campaign = convert_campaign_for_tv_planner(projects_crm_campaign)
    
    # Check if already exists in local database
    try:
        existing_campaigns = models.list_campaigns()
        for existing in existing_campaigns:
            if existing.get('name') == tv_campaign['name']:
                logger.info(f"Campaign {tv_campaign['name']} already exists locally")
                return existing['id']
    except:
        pass
    
    # Create in local database
    local_campaign_id = models.create_campaign(
        name=tv_campaign['name'],
        start_date=tv_campaign['start_date'],
        end_date=tv_campaign['end_date'], 
        agency=tv_campaign['agency'],
        client=tv_campaign['client'],
        product=tv_campaign['product'],
        country=tv_campaign['country']
    )
    
    logger.info(f"Synced Projects-CRM campaign {actual_crm_id} to local campaign {local_campaign_id}")
    return local_campaign_id


def get_local_campaign_id(campaign_id):
    """Get or create local campaign ID for Projects-CRM campaigns"""
    if str(campaign_id).startswith('crm_'):
        # This is a Projects-CRM campaign, sync it to local database
        return sync_projects_crm_campaign_to_local(campaign_id)
    else:
        # This is already a local campaign
        return int(campaign_id)