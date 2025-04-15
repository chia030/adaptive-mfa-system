<!-- src/MFASelection.svelte -->
<script>
    import { createEventDispatcher } from 'svelte';
    export let methods = [];
    const dispatch = createEventDispatcher();
    
    function selectMethod(method) {
      dispatch('select', method);
    }
  </script>
  
  <div>
    <h2>Select an MFA Method</h2>
    {#each methods as method}
      <button on:click={() => selectMethod(method)}>
        {method.name}
      </button>
    {/each}
  </div>
  