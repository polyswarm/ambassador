import logging
import random
import os

from polyswarmclient.ambassador import Ambassador

ARTIFACT_DIRECTORY = os.getenv('ARTIFACT_DIRECTORY', 'docker/artifacts')

class FilesystemAmbassador(Ambassador):
    """Ambassador which submits artifacts from a directory"""

    async def next_bounty(self, chain):
        """Submit either the EICAR test string or a benign sample

        Returns:
            (int, str, int): Tuple of amount, ipfs_uri, duration, None to terminate submission

            amount (int): Amount to place this bounty for
            ipfs_uri (str): IPFS URI of the artifact to post
            duration (int): Duration of the bounty in blocks
        """
        amount = self.client.bounties.parameters[chain]['bounty_amount_minimum']
        filename = os.path.join(ARTIFACT_DIRECTORY, random.choice(os.listdir(ARTIFACT_DIRECTORY)))
        duration = 20

        logging.info('Submitting file %s', filename)
        ipfs_uri = await self.client.post_artifacts([(filename, None)])
        if not ipfs_uri:
            logging.error('Could not submit artifact to IPFS')
            return None

        return amount, ipfs_uri, duration
